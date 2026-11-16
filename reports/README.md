# Academic report artifacts

- **CLOAK_Project_Report.docx** — editable academic report with a cached chapter-level table of contents and a refreshable Word field.
- **CLOAK_Project_Report.pdf** — separately typeset, checked PDF using the same report content. It is not an export from Word; DOCX pagination can differ by editor.
- **manuscript.md** — editable body prose, 30 sections, approximately 6,300 words; section 3.5 explains the implemented TCP transport.
- **references.json** — fifteen verified primary documentation/standards references, cited in first-appearance order.
- **report_validation.json** — PDF pagination and document-generation evidence.
- **FINAL_CHECKS.md**, **gui_checks.json** — actual verification evidence and limits.
- **assets/** — diagrams and authentic app captures. The chat capture contains an overlapping macOS screen-recording permission dialog; replace it with an unobstructed capture for final submission.

The complete PDF is **34 pages**, including all preliminary pages, references, selected code excerpts, and screenshots. This follows the revised 30–35 total-page requirement. The body occupies 24 pages; 30 sections are grouped where their topics overlap. The full runnable source is supplied in the project rather than printed in its entirety. Times New Roman, 12pt body, 1.5 spacing, 16pt bold chapter/subtitle headings, one-inch left and half-inch right margins are used. Main-matter page numbering starts at Chapter 1 and continues through appendices. References, figures, and the results table are numbered. The cover and certificate identify Chris Jonathan, Bhaskar Tripathi, and Neil Sahay, Team Kernel Knights, Section U1, under Dr.NALLARASAN V of NWC. The project title is “Encrypted-chat service”. The guide designation is intentionally blank. No specialization was supplied, so no specialization qualifier is printed. Institution details remain unchanged. Signatures are blank.

## Fill in academic details

The supplied details are saved in `reports/identity.json`. Edit that file to change them, then rebuild:

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

The supplied template requires Turnitin verification with similarity no more than 10%, arranged through the guide, and proof for any claimed publication. No Turnitin report, similarity score, publication, or supervisor approval has been fabricated. No publication is claimed. Obtain institutional verification, confirm identity details, and collect the required signatures before submission.
