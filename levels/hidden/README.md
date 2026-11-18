# Hidden levels

This directory holds the owner's hidden levels, one `.txt` file per level in `tier<N>/` directories,
with opaque names such as `hidden/tier2/h-07`. The agent can reach them only through `golem validate`,
and for each one it learns only whether its program passed.

Nothing in this directory except this README is committed. `.gitignore` excludes the rest, because the
repository is public and a published hidden level would let a program be fitted to it. Never copy a
hidden level into an issue, a commit, a log or a test. Tests use the fixture hidden levels in
`tests/fixtures/hidden/` instead.
