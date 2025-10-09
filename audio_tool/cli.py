import argparse

from audio_tool.core import (
    list_sessions_verbose,
    set_volume_by_name,
    _interactive_set_volume,
    toggle_volume
)


def main():
    parser = argparse.ArgumentParser(description="Control application volumes on Windows")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all audio applications active")

    # select
    subparsers.add_parser("select", help="Interactively select an application and change its volume")

    # set
    set_parser = subparsers.add_parser("set", help="Set volume for an application")
    set_parser.add_argument("app_name")
    set_parser.add_argument("volume")

    # toggle
    toggle_parser = subparsers.add_parser("toggle", help="Toggle mute for an app")
    toggle_parser.add_argument("app_name")

    # cdda
    subparsers.add_parser("cdda", help="Toggle CDDA's volume on and off")

    args = parser.parse_args()

    match args.command:
        case "list":
            for session, _ in list_sessions_verbose():
                print(session)
        case "select":
            sessions = list_sessions_verbose(list_pos=True)
            if not sessions:
                print("No audio sessions found.")
                pass

            sessions_print, sessions_raw = zip(*sessions)
            for session_formatted in sessions_print:
                print(session_formatted)

            results = _interactive_set_volume(sessions_raw)
            for r in results:
                if r.error:
                    print(r.error.value)
                else:
                    print(f"Volume of {r.name} set to {r.volume * 100:.0f}%")
        case "set":
            results = set_volume_by_name(args.app_name, args.volume)
            for r in results:
                if r.error:
                    print(r.error.value)
                else:
                    print(f"Volume of {r.name} set to {r.volume * 100:.0f}%")
        case "toggle":
            results = toggle_volume(args.app_name)
            for r in results:
                if r.error:
                    print(r.error.value)
                else:
                    mute_status = "muted" if r.muted else "unmuted"
                    print(f"{r.name} is now {mute_status}.")
        case "cdda":
            # Special case for Cataclysm DDA
            new_vol = toggle_volume("cataclysm-tiles.exe")
            for r in new_vol:
                if r.error:
                    print(r.error.value)
                else:
                    mute_status = "muted" if r.muted else "unmuted"
                    print(f"CDDA is now {mute_status}.")



if __name__ == "__main__":
    main()