"""
Shows a small GUI window prompting for Twitch credentials when the bot
detects that TWITCH_REFRESH_TOKEN or TWITCH_CLIENT_ID are missing or
still placeholder values in .env.

Runs synchronously before the asyncio bot loop starts, so there are no
threading or event-loop conflicts. Uses only tkinter, which is already
bundled with Python and available in PyInstaller windowed builds (it is
pulled in as a hidden import by pystray anyway).

Returns True if the user successfully provided credentials and they were
saved to .env, or False if they cancelled -- in which case the bot still
starts but auto-refresh will not be available.
"""
import logging
import os
import re
import tkinter as tk
from tkinter import messagebox

import config

log = logging.getLogger("credential_prompt")

PLACEHOLDER = ""  # empty string means not filled in


def _is_missing(value: str) -> bool:
    return not value or not value.strip()


def needs_credentials() -> bool:
    """Returns True if either required token field is missing/empty."""
    return _is_missing(config.TWITCH_REFRESH_TOKEN) or _is_missing(config.TWITCH_CLIENT_ID)


def prompt_for_credentials() -> bool:
    """
    Opens a small window asking for the refresh token and client ID.
    Writes the values to .env and updates config in-memory if the user
    confirms. Returns True if saved successfully, False if cancelled.
    """
    root = tk.Tk()
    root.title("Twitch bot setup")
    root.resizable(False, False)

    # Centre on screen
    root.update_idletasks()
    w, h = 520, 320
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")

    saved = {"ok": False}

    # --- Header ---
    header = tk.Label(
        root,
        text="Token refresh setup needed",
        font=("Segoe UI", 13, "bold"),
        pady=10,
    )
    header.pack()

    info = tk.Label(
        root,
        text=(
            "To keep the bot connected indefinitely without manually\n"
            "regenerating tokens, add your refresh token and client ID.\n\n"
            "Get both from https://twitchtokengenerator.com\n"
            "(generate a new Bot Chat Token -- all three values are shown)."
        ),
        font=("Segoe UI", 9),
        justify="center",
        pady=4,
    )
    info.pack()

    # --- Fields ---
    frame = tk.Frame(root, pady=8)
    frame.pack(fill="x", padx=24)

    tk.Label(frame, text="Refresh token:", anchor="w", font=("Segoe UI", 9)).grid(
        row=0, column=0, sticky="w", pady=4
    )
    refresh_var = tk.StringVar(value=config.TWITCH_REFRESH_TOKEN or "")
    refresh_entry = tk.Entry(frame, textvariable=refresh_var, width=52, show="*")
    refresh_entry.grid(row=0, column=1, padx=8)

    tk.Label(frame, text="Client ID:", anchor="w", font=("Segoe UI", 9)).grid(
        row=1, column=0, sticky="w", pady=4
    )
    client_id_var = tk.StringVar(value=config.TWITCH_CLIENT_ID or "")
    client_id_entry = tk.Entry(frame, textvariable=client_id_var, width=52)
    client_id_entry.grid(row=1, column=1, padx=8)

    # --- Buttons ---
    def on_save():
        refresh = refresh_var.get().strip()
        client_id = client_id_var.get().strip()

        if not refresh or not client_id:
            messagebox.showerror(
                "Missing values",
                "Both fields are required. Leave blank to skip for now.",
                parent=root,
            )
            return

        if _write_to_env(refresh, client_id):
            config.TWITCH_REFRESH_TOKEN = refresh
            config.TWITCH_CLIENT_ID = client_id
            saved["ok"] = True
            root.destroy()
        else:
            messagebox.showerror(
                "Could not save",
                f"Failed to write to .env at:\n{os.path.join(config.base_dir, '.env')}\n\n"
                "Check the file isn't locked or read-only.",
                parent=root,
            )

    def on_skip():
        log.warning(
            "Credential prompt skipped -- auto-refresh will not be available "
            "until TWITCH_REFRESH_TOKEN and TWITCH_CLIENT_ID are added to .env"
        )
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="Save and continue", command=on_save, width=18).pack(
        side="left", padx=8
    )
    tk.Button(btn_frame, text="Skip for now", command=on_skip, width=14).pack(
        side="left", padx=8
    )

    root.protocol("WM_DELETE_WINDOW", on_skip)
    root.mainloop()

    return saved["ok"]


def _write_to_env(refresh_token: str, client_id: str) -> bool:
    env_path = os.path.join(config.base_dir, ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Update or append TWITCH_REFRESH_TOKEN
        if "TWITCH_REFRESH_TOKEN=" in content:
            content = re.sub(
                r"TWITCH_REFRESH_TOKEN=.*",
                f"TWITCH_REFRESH_TOKEN={refresh_token}",
                content,
            )
        else:
            content += f"\nTWITCH_REFRESH_TOKEN={refresh_token}\n"

        # Update or append TWITCH_CLIENT_ID
        if "TWITCH_CLIENT_ID=" in content:
            content = re.sub(
                r"TWITCH_CLIENT_ID=.*",
                f"TWITCH_CLIENT_ID={client_id}",
                content,
            )
        else:
            content += f"TWITCH_CLIENT_ID={client_id}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        log.info("Credentials saved to .env successfully")
        return True

    except OSError as e:
        log.error(f"Could not write credentials to .env: {e}")
        return False
