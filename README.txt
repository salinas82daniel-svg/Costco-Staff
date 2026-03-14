Grinding / Bundling Flow Simulator

Files included:
- app.py
- requirements.txt
- .github/workflows/build.yml

Purpose:
- Show normal grinding flow
- Show bundle mode with trays diverted to the bundle line
- Show that yellow grinding labor gets pulled into orange bundle positions
- Show optional dedicated blue bundle labor
- Let leadership see why existing line labor cannot be in two places at once

How to run locally:
1. Install Python 3.11+
2. pip install -r requirements.txt
3. python app.py

How to build EXE in GitHub:
1. Create a GitHub repo
2. Upload all files, including .github/workflows/build.yml
3. Push to main
4. Open the Actions tab
5. Run "Build Windows EXE"
6. Download the EXE artifact

Talking point:
"The line is a series circuit. Once positions 4,5,6,7,8 move to bundling, they are no longer available to run their original grinding stations."
