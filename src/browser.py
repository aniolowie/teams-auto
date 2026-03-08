"""
browser.py
Handles all Playwright-based interactions with Microsoft Teams:
  - Login and session persistence
  - Fetching assignment details
  - Uploading completed files and turning in
"""

import os
import json
import logging
from playwright.async_api import async_playwright
from config import TEAMS_EMAIL, TEAMS_PASSWORD, STATE_FILE

logger = logging.getLogger(__name__)

TEAMS_URL = "https://teams.microsoft.com/"
ASSIGNMENTS_URL = "https://teams.microsoft.com/v2/?app=assignments"


async def _make_context(p, headless=True):
    """Creates a browser context, reusing saved session state if available."""
    browser = await p.chromium.launch(headless=headless)
    if os.path.exists(STATE_FILE):
        context = await browser.new_context(storage_state=STATE_FILE)
        logger.info("Loaded existing session state.")
    else:
        context = await browser.new_context()
        logger.info("No session state found, starting fresh.")
    return browser, context


async def login_to_teams():
    """
    Logs into Microsoft Teams using credentials from .env and saves the
    session state (cookies + localStorage) to STATE_FILE so subsequent
    runs do not need to log in again.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        logger.info("Navigating to Teams login page...")
        await page.goto(TEAMS_URL)

        # --- Email step ---
        await page.wait_for_selector("input[type='email']", timeout=30000)
        await page.fill("input[type='email']", TEAMS_EMAIL)
        await page.click("input[type='submit']")

        # --- Password step ---
        await page.wait_for_selector("input[type='password']", timeout=30000)
        await page.fill("input[type='password']", TEAMS_PASSWORD)
        await page.click("input[type='submit']")

        # --- "Stay signed in?" prompt ---
        try:
            await page.wait_for_selector("input[type='submit']", timeout=10000)
            await page.click("input[type='submit']")
        except Exception:
            pass  # Prompt may not appear

        # Wait for Teams shell to load
        await page.wait_for_selector("div[data-tid='app-layout']", timeout=90000)
        logger.info("Login successful.")

        await context.storage_state(path=STATE_FILE)
        logger.info(f"Session state saved to {STATE_FILE}")
        await browser.close()


async def fetch_assignments() -> list[dict]:
    """
    Navigates to the Assignments tab and scrapes all active assignments.
    Returns a list of dicts with keys: id, title, due_date, instructions, class_name.

    NOTE: Playwright selectors are based on the Teams web app as of early 2025.
    If Microsoft updates the UI, selectors may need adjustment.
    """
    if not os.path.exists(STATE_FILE):
        logger.info("No session found. Logging in first...")
        await login_to_teams()

    async with async_playwright() as p:
        browser, context = await _make_context(p)
        page = await context.new_page()

        logger.info("Navigating to Assignments tab...")
        await page.goto(ASSIGNMENTS_URL)

        try:
            await page.wait_for_selector("[data-tid='assignment-card']", timeout=30000)
        except Exception:
            logger.warning("No assignment cards found. Session may have expired.")
            await browser.close()
            # Invalidate session and retry once
            os.remove(STATE_FILE)
            await login_to_teams()
            return await fetch_assignments()

        assignments = []
        cards = await page.query_selector_all("[data-tid='assignment-card']")

        for i, card in enumerate(cards):
            try:
                title_el = await card.query_selector("[data-tid='assignment-title']")
                due_el = await card.query_selector("[data-tid='assignment-due-date']")
                class_el = await card.query_selector("[data-tid='assignment-class-name']")

                title = await title_el.inner_text() if title_el else f"Assignment {i+1}"
                due = await due_el.inner_text() if due_el else "No due date"
                class_name = await class_el.inner_text() if class_el else "Unknown class"

                # Click into the assignment to get full instructions
                await card.click()
                await page.wait_for_selector("[data-tid='assignment-details-pane']", timeout=10000)

                instructions_el = await page.query_selector("[data-tid='assignment-instructions']")
                instructions = await instructions_el.inner_text() if instructions_el else "No instructions provided."

                assignments.append({
                    "id": f"assignment_{i}",
                    "title": title.strip(),
                    "due_date": due.strip(),
                    "class_name": class_name.strip(),
                    "instructions": instructions.strip(),
                })

                # Go back to list
                back_btn = await page.query_selector("[data-tid='back-button']")
                if back_btn:
                    await back_btn.click()
                    await page.wait_for_selector("[data-tid='assignment-card']", timeout=10000)

            except Exception as e:
                logger.warning(f"Failed to parse assignment card {i}: {e}")

        await browser.close()
        logger.info(f"Fetched {len(assignments)} assignment(s).")
        return assignments


async def upload_and_turn_in(file_path: str, assignment_id: str):
    """
    Navigates to the given assignment, uploads the completed file,
    and clicks 'Turn in'.

    assignment_id should match the 'id' field returned by fetch_assignments().
    """
    if not os.path.exists(STATE_FILE):
        await login_to_teams()

    async with async_playwright() as p:
        browser, context = await _make_context(p)
        page = await context.new_page()

        logger.info(f"Navigating to assignment {assignment_id} for upload...")
        await page.goto(ASSIGNMENTS_URL)
        await page.wait_for_selector("[data-tid='assignment-card']", timeout=30000)

        # Find and click the correct assignment card
        cards = await page.query_selector_all("[data-tid='assignment-card']")
        index = int(assignment_id.split("_")[-1])
        if index < len(cards):
            await cards[index].click()
        else:
            raise ValueError(f"Assignment index {index} out of range.")

        await page.wait_for_selector("[data-tid='assignment-details-pane']", timeout=15000)

        # Click "Add work" or file upload button
        add_work_btn = await page.query_selector("[data-tid='add-work-button']")
        if add_work_btn:
            await add_work_btn.click()
        else:
            raise RuntimeError("Could not find 'Add work' button. Teams UI may have changed.")

        # Handle file upload dialog
        async with page.expect_file_chooser() as fc_info:
            upload_btn = await page.query_selector("[data-tid='upload-from-device']")
            if upload_btn:
                await upload_btn.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(file_path)

        await page.wait_for_timeout(3000)  # Wait for upload to complete

        # Click "Turn in"
        turn_in_btn = await page.query_selector("[data-tid='turn-in-button']")
        if turn_in_btn:
            await turn_in_btn.click()
            await page.wait_for_timeout(3000)
            logger.info("Assignment turned in successfully.")
        else:
            raise RuntimeError("Could not find 'Turn in' button.")

        await browser.close()
