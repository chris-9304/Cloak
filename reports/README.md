# Academic report artifacts

- **CLOAK_Project_Report.docx** — editable academic report with a Word table-of-contents field.
- **CLOAK_Project_Report.pdf** — separately typeset, checked PDF using the same report content. It is not an export from Word; DOCX pagination can differ by editor.
- **manuscript.md** — editable body prose, 30 sections, approximately 6,700 words.
- **references.json** — fifteen verified primary documentation/standards references, cited in first-appearance order.
- **report_validation.json** — PDF pagination and document-generation evidence.
- **FINAL_CHECKS.md**, **gui_checks.json** — actual verification evidence and limits.
- **assets/** — diagrams and authentic app captures. The chat capture contains an overlapping macOS screen-recording permission dialog; replace it with an unobstructed capture for final submission.

The PDF contains at least 30 main-body pages before references, excluding code and screenshots. Times New Roman, 12pt body, 1.5 spacing, 16pt bold chapter/subtitle headings, one-inch left and half-inch right margins are used. Main-matter page numbering starts at Chapter 1 and continues through appendices. References, figures, and the results table are numbered. Cover and certificate fields remain clearly marked because academic identity details have not been supplied. Signatures are blank.

## Fill in academic details

Create `reports/identity.json` with real values, then rebuild:

```json
{
  "students": "STUDENT ONE [REGISTRATION NUMBER]\nSTUDENT TWO [REGISTRATION NUMBER]",
  "guide": "GUIDE NAME",
  "designation": "GUIDE DESIGNATION",
  "department": "GUIDE DEPARTMENT",
  "specialization": "SPECIALIZATION"
}
```

```sh
chat_env/bin/python -m pip install -r requirements-report.txt
chat_env/bin/python build_report.py
```

The builder reads Times New Roman font files from `/System/Library/Fonts/Supplemental` on macOS. Set `TIMES_FONT_DIR` to a directory containing Times New Roman.ttf, Times New Roman Bold.ttf, and Times New Roman Italic.ttf on another system.

Open the DOCX in Word and update its contents field (select the field and choose Update Table). Review final pagination after substituting names or changing content. The PDF has checked pagination; the DOCX has structural formatting checks and has not been rendered in Word here.

## External submission requirements

The supplied template requires Turnitin verification with similarity no more than 10%, arranged through the guide, and proof for any claimed publication. No Turnitin report, similarity score, publication, or supervisor approval has been fabricated. No publication is claimed. Obtain institutional verification, replace identity fields, and collect the required signatures before submission.
