# The two trees are audit fixtures, read by auditors, not part of the repo's
# test run (their modules share names, and broken/ plants dishonest tests).
collect_ignore_glob = ["broken/*", "clean/*"]
