"""PyInstaller runtime hook for Linux Tcl/Tk standalone environment.

Ensures that bundled Tcl/Tk data assets and dynamic libraries are correctly
located by Tkinter at runtime when running from a PyInstaller onefile binary.
"""
import os
import sys


def _setup_linux_tcltk():
    if not getattr(sys, "frozen", False):
        return

    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return

    # Look for tcl data dir
    tcl_candidates = [
        os.path.join(meipass, "_tcl_data"),
        os.path.join(meipass, "_tcl_data", "tcl8.6"),
        os.path.join(meipass, "tcl8.6"),
        os.path.join(meipass, "tcl"),
    ]
    for cand in tcl_candidates:
        if os.path.isdir(cand) and (
            os.path.exists(os.path.join(cand, "init.tcl"))
            or os.path.exists(os.path.join(cand, "tcl8.6", "init.tcl"))
        ):
            if os.path.exists(os.path.join(cand, "init.tcl")):
                os.environ["TCL_LIBRARY"] = cand
            else:
                os.environ["TCL_LIBRARY"] = os.path.join(cand, "tcl8.6")
            break

    # Look for tk data dir
    tk_candidates = [
        os.path.join(meipass, "_tk_data"),
        os.path.join(meipass, "_tk_data", "tk8.6"),
        os.path.join(meipass, "tk8.6"),
        os.path.join(meipass, "tk"),
    ]
    for cand in tk_candidates:
        if os.path.isdir(cand):
            if os.path.exists(os.path.join(cand, "tk.tcl")):
                os.environ["TK_LIBRARY"] = cand
            elif os.path.exists(os.path.join(cand, "tk8.6", "tk.tcl")):
                os.environ["TK_LIBRARY"] = os.path.join(cand, "tk8.6")
            else:
                os.environ["TK_LIBRARY"] = cand
            break


_setup_linux_tcltk()
