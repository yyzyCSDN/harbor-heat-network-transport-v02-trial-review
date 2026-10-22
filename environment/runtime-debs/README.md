# Terminal runtime packages

These Debian amd64 packages provide tmux 3.3a-3 and its two extra runtime dependencies for Harbor Terminus2. They were obtained with apt's normal signed Debian bookworm/bookworm-security repository validation on 2026-10-22; no unauthenticated-package override was used. Their exact bytes are checked with SHA256SUMS before offline dpkg installation. Package license/copyright notices are installed under /usr/share/doc by dpkg. This task targets Linux amd64.

libevent-core-2.1-7: 2.1.12-stable-8+deb12u1
libutempter0: 1.2.1-3
tmux: 3.3a-3

The terminal recorder asciinema 2.4.0 is separately hash-locked in requirements.txt. These are general terminal tools, with no test inputs or reference answers.
