#!/bin/sh
# Switch AeroSpace into 'passthrough' mode while a guest-OS *session* window is
# focused, so alt-tab and all other AeroSpace grabs fall through to the guest
# instead of being eaten by the tiling WM.
#
# Each app below serves its launcher and its session windows under one bundle id,
# so sessions are told apart by window title:
#   com.microsoft.rdc.macos  Remote Desktop / "Windows App". Launcher titles are
#                            the sidebar tabs; a session is titled after the
#                            remote machine.
#   com.utmapp.UTM           Library window is titled "UTM"; a running VM's
#                            display window is titled after the VM ("Debian XFCE").
#
# Any non-session focus (launcher included, or any other app) returns to 'main'.
#
# focus-follows-mouse stays off unconditionally (set in aerospace.toml); this
# script no longer rewrites that key.
#
# Fired from on-focus-changed.

focused=$(aerospace list-windows --focused --format '%{app-bundle-id}|%{window-title}' 2>/dev/null)
bundle=${focused%%|*}
title=${focused#*|}

session=0
case "$bundle" in
    com.microsoft.rdc.macos)
        case "$title" in
            # Launcher / connection-center windows -> stay in main
            Favorites|Devices|Apps|"Windows App"|"Microsoft Remote Desktop") ;;
            # Anything else with this bundle id is a live remote session
            *) session=1 ;;
        esac
        ;;
    com.utmapp.UTM)
        case "$title" in
            # Library window and auxiliary panels -> stay in main
            UTM|Settings|Preferences|"") ;;
            # Anything else with this bundle id is a running VM display
            *) session=1 ;;
        esac
        ;;
    com.vmware.fusion)
        case "$title" in
            # Library / settings windows -> stay in main
            "VMware Fusion"|"Virtual Machine Library"|Settings|Preferences|"") ;;
            # Anything else with this bundle id is a running VM display
            *) session=1 ;;
        esac
        ;;
esac

if [ "$session" = 1 ]; then
    aerospace mode passthrough
else
    aerospace mode main
fi
