# Working on XTV-SupportBot

## PR workflow
- **Always open PRs against `main`**, never against another feature branch.
  Stacked PRs caused a merge-chain accident once — commits from phase PRs
  landed on intermediate branches instead of main. Default to `base=main`.

## Commit conventions
- Author identity: `𝕏0L0™ <davdxpx@gmail.com>` on every commit.
- No session links in commit or PR bodies.
- Footer either empty or `Developed by @davdxpx`.

## Comments in code
- Default to no comments. Only add one when the WHY is non-obvious.
- Don't narrate what the code does — well-named identifiers do that.
- No long PR descriptions either — tight bullets, no prose.
