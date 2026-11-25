@echo off
rem Ouvre/continue la session ESPRIEATHER avec le modele local non censure.
set CLI=C:\Users\aether\AppData\Local\Programs\ai.opencode.desktop\resources\opencode-cli.exe
"%CLI%" run --model esprieather/dolphin3 --session ses_e04a74871ffexFHvNy4uGt1knu --title "ESPRIEATHER uncensored" %*
