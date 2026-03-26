"""Entry point to run the GOATGuard agent."""

import sys
sys.path.insert(0, "src")

from goatguard_agent.consent import revoke_consent

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--revoke-consent":
        revoke_consent()
        sys.exit(0)

    from goatguard_agent.main import main
    main()