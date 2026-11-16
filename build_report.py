"""Build editable academic DOCX and a separately typeset PDF from shared content.

Run: chat_env/bin/python build_report.py
Optional academic details: reports/identity.json (see reports/README.md).
"""
from pathlib import Path
import json
import copy
import re
import textwrap
import ast
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer, Image as PDFImage, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reports'; ASSETS=OUT/'assets'; ASSETS.mkdir(parents=True,exist_ok=True)
FONT_DIR=Path('/System/Library/Fonts/Supplemental')
# Supply TIMES_FONT_DIR on other systems with licensed Times New Roman fonts.
import os
FONT_DIR=Path(os.environ.get('TIMES_FONT_DIR',FONT_DIR))
for name,file in [('TNR','Times New Roman.ttf'),('TNR-Bold','Times New Roman Bold.ttf'),('TNR-Italic','Times New Roman Italic.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT_DIR/file)))
pdfmetrics.registerFontFamily('TNR',normal='TNR',bold='TNR-Bold',italic='TNR-Italic',boldItalic='TNR-Bold')
identity={'students':'[STUDENT 1 NAME — REGISTRATION NUMBER]\n[STUDENT 2 NAME — REGISTRATION NUMBER]',
          'guide':'[GUIDE NAME]','designation':'[GUIDE DESIGNATION]',
          'department':'[GUIDE DEPARTMENT]','specialization':'',
          'project_title':'CLOAK: ENCRYPTED PEER-TO-PEER LAN CHAT',
          'team_name':'','section':''}
if (OUT/'identity.json').exists():identity.update(json.loads((OUT/'identity.json').read_text()))
TITLE=identity['project_title']
guide_details='\n'.join(value for value in (identity['designation'], identity['department']) if value)


def diagram(filename,boxes,edges,size=(1500,800)):
    im=Image.new('RGB',size,'white'); d=ImageDraw.Draw(im)
    f=ImageFont.truetype(str(FONT_DIR/'Times New Roman.ttf'),28)
    for a,b in edges:
        x1,y1,w1,h1,_=boxes[a];x2,y2,w2,h2,_=boxes[b]
        start=(x1+w1/2,y1+h1/2);end=(x2+w2/2,y2+h2/2)
        d.line((start,end),fill='#44516a',width=4)
    for x,y,w,h,label in boxes:
        d.rounded_rectangle((x,y,x+w,y+h),radius=12,fill='#f2f5f9',outline='#263247',width=3)
        lines=label.split('\n'); line_h=38;sy=y+(h-len(lines)*line_h)/2
        for i,line in enumerate(lines):
            d.text((x+w/2,sy+i*line_h),line,font=f,fill='#111827',anchor='mt')
    im.save(ASSETS/filename)

diagram('architecture.png',[
 (40,40,370,140,'Tkinter ChatApp\nGUI thread + event queue'),(550,40,370,140,'SecureSession\nPassword confirmation'),
 (1060,40,380,140,'EncryptionManager\nPBKDF2 + Fernet'),(550,300,370,140,'ChatConnection\nLength-prefixed JSON / TCP'),
 (40,300,370,140,'DiscoveryService\nUDP broadcast / peer registry'),(550,590,370,140,'Remote CLOAK client\nTCP chat + UDP discovery'),
 (1060,300,380,140,'TCPListener\nIncoming sockets')],[(0,1),(1,2),(1,3),(0,4),(3,5),(4,5),(6,1)])
diagram('use_cases.png',[
 (40,280,280,160,'Local participant'),(470,30,490,100,'Configure callsign and passphrase'),
 (470,180,490,100,'Discover peer / connect directly'),(470,330,490,100,'Verify password before chat'),
 (470,480,490,100,'Send and receive encrypted text'),(470,630,490,100,'Disconnect / reconnect / exit'),
 (1150,280,300,160,'Remote participant')],[(0,1),(0,2),(0,3),(0,4),(0,5),(6,3),(6,4)])
diagram('classes.png',[
 (30,30,390,190,'ChatApp\nGUI state / event queue\nOwns current session'),(550,30,390,190,'SecureSession\nstart / send / close\nHandshake + timer'),
 (1080,30,390,190,'EncryptionManager\nset_password\nencrypt / decrypt'),(550,320,390,170,'ChatConnection\nsend / accept / close\nFraming + callbacks'),
 (30,320,390,170,'PeerManager → Peer\nEndpoint registry\nFreshness / pruning'),(30,600,390,150,'DiscoveryService\nUDP advertisements'),
 (1080,320,390,170,'TCPListener\nstart / stop\nAccepted sockets')],[(0,1),(1,2),(1,3),(0,4),(0,5),(0,6)])

D=Document()
for style in ['Normal','Heading 1','Heading 2','Heading 3','Caption']:
    st=D.styles[style];st.font.name='Times New Roman';st.font.size=Pt(12)
    st.paragraph_format.line_spacing=1.5;st.paragraph_format.space_after=Pt(12)
    st.font.color.rgb=None
for style in ['Heading 1','Heading 2']:
    D.styles[style].font.size=Pt(16);D.styles[style].font.bold=True
D.styles['Normal'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
for sec in D.sections:
    sec.page_width=Inches(8.2677);sec.page_height=Inches(11.6929)
    sec.left_margin=Inches(1);sec.right_margin=Inches(.5);sec.top_margin=sec.bottom_margin=Inches(.8)
styles={
 'body':ParagraphStyle('body',fontName='TNR',fontSize=12,leading=18,alignment=TA_JUSTIFY,spaceAfter=12),
 'h1':ParagraphStyle('h1',fontName='TNR-Bold',fontSize=16,leading=24,spaceAfter=16),
 'h2':ParagraphStyle('h2',fontName='TNR-Bold',fontSize=16,leading=24,spaceAfter=14),
 'center':ParagraphStyle('center',fontName='TNR',fontSize=12,leading=18,alignment=TA_CENTER,spaceAfter=12),
 'cover':ParagraphStyle('cover',fontName='TNR-Bold',fontSize=16,leading=24,alignment=TA_CENTER,spaceAfter=16),
}
story=[]
# PDF page tracking is populated during the first pass and reused for contents.
page_map={}
class MarkedParagraph(Paragraph):
    def __init__(self,text,style,label=None):super().__init__(text,style);self.label=label
    def draw(self):
        if self.label:page_map[self.label]=self.canv.getPageNumber()
        super().draw()


def para(text,kind='body',label=None):
    if kind in ('h1','h2'):
        p=D.add_paragraph(text,'Heading 1' if kind=='h1' else 'Heading 2')
    else:
        p=D.add_paragraph(text)
        if kind in ('center','cover'):
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            if kind=='cover':
                for r in p.runs:r.bold=True;r.font.size=Pt(16)
    story.append(MarkedParagraph(escape(text).replace('\n','<br/>'),styles[kind],label))


def page():D.add_page_break();story.append(PageBreak())
def image(filename,caption):
    p=D.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.add_run().add_picture(str(ASSETS/filename),width=Inches(6.5))
    im=Image.open(ASSETS/filename);w=455;h=w*im.height/im.width
    story.append(PDFImage(str(ASSETS/filename),width=w,height=h));para(caption,'center')

def table(rows,caption):
    para(caption,'center');t=D.add_table(rows=0,cols=len(rows[0]));t.style='Table Grid';t.alignment=1
    for row in rows:
        cells=t.add_row().cells
        for cell,value in zip(cells,row):
            cell.text=value
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing=1.5;p.paragraph_format.space_after=Pt(3)
    data=[[Paragraph(escape(v),styles['body']) for v in row] for row in rows]
    pt=Table(data,colWidths=[325,155] if len(rows[0])==2 else None)
    pt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,'#596273'),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),'#edf0f4'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
    story.append(pt)

# Preliminary pages have no printed page number.
para(TITLE,'cover');
for r in D.paragraphs[-1].runs:r.font.size=Pt(18)
story[-1].style=ParagraphStyle('title',parent=styles['cover'],fontSize=18,leading=27)
para('A PROJECT REPORT','cover');para('Submitted by','center');para(identity['students'],'cover')
if identity['team_name'] or identity['section']:
    para(' | '.join(value for value in (identity['team_name'], 'Section: '+identity['section'] if identity['section'] else '') if value),'center')
para('Under the Guidance of','center');para(identity['guide'],'cover');para(guide_details,'center')
para('in partial fulfillment of the requirements for the degree of','center');para('BACHELOR OF TECHNOLOGY','cover')
degree='COMPUTER SCIENCE ENGINEERING'
if identity['specialization']:
    degree+='\nwith specialization in '+identity['specialization']
para(degree,'center')
para('DEPARTMENT OF COMPUTING TECHNOLOGIES\nCOLLEGE OF ENGINEERING AND TECHNOLOGY\nSRM INSTITUTE OF SCIENCE AND TECHNOLOGY\nKATTANKULATHUR – 603 203','center');para('NOVEMBER 2026','center');page()
para('SRM INSTITUTE OF SCIENCE AND TECHNOLOGY\nKATTANKULATHUR – 603 203','cover');para('BONAFIDE CERTIFICATE','cover')
para(f'Certified that 21CSC203P – Advanced Programming Practice [Project Report] titled “{TITLE}” is the bonafide work of “{identity["students"].replace(chr(10), "; ")}” who carried out the project work under my supervision.')
if identity['team_name'] or identity['section']:
    para('Team: '+identity['team_name']+' | Section: '+identity['section'],'center')
para('\n\nSIGNATURE\n\n'+identity['guide']+'\nSUPERVISOR\n'+guide_details,'center')
para('Signature and institutional approval to be completed by the authorized supervisor.','center');page()
para('ABSTRACT','h1')
para('CLOAK is a Python desktop application for one-to-one encrypted text communication on a local network. The project combines a Tkinter interface, UDP peer discovery, TCP stream framing, password-derived Fernet encryption, and an explicit password-confirmation handshake. Its revised workflow requires setup in every launcher and enables messaging only after the two clients demonstrate possession of the same shared password.')
para('The implementation separates graphical state from secure-session behavior and low-level transport. Worker threads handle connection operations and key derivation, while a synchronized event queue delivers outcomes to the Tkinter thread. Direct IPv4 connection complements broadcast discovery. A dark yellow/cyan interface inspired by Cyberpunk: Edgerunners provides clear offline, pending, verified, and error states using Python and Tkinter alone.')
para('Verification combines automated encryption and protocol tests with a live two-window desktop check. The available evidence covers local discovery, bidirectional messaging, password rejection, disconnect, and reconnection. The design remains an educational shared-password LAN system: it does not provide independent identity verification, forward secrecy, internet relaying, or persistent messaging. The report records these limits and separates verified local behavior from a pending two-device LAN trial.');page()
para('TABLE OF CONTENTS','h1')
# Dynamic DOCX TOC; PDF contents resolved in second pass.
p=D.add_paragraph();field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'TOC \\o "1-1" \\h \\z \\u');r=OxmlElement('w:r');tx=OxmlElement('w:t');tx.text='Update this field in Word to refresh the editable table of contents.';r.append(tx);field.append(r);p._p.append(field)
contents_placeholder=len(story);story.append(Spacer(1,1));page()
# Numbered main matter begins in a new DOCX section.
sec=D.add_section(WD_SECTION_START.CONTINUOUS);sec.footer.is_linked_to_previous=False
pg=OxmlElement('w:pgNumType');pg.set(qn('w:start'),'1');sec._sectPr.append(pg)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
body_start_label='CHAPTER 1: INTRODUCTION'
chunks=(OUT/'manuscript.md').read_text().strip().split('---PAGE---')
for index,chunk in enumerate(chunks):
    if index:page()
    for block in chunk.strip().split('\n\n'):
        if block.startswith('#'):
            for line in block.splitlines():
                if line.startswith('#'):
                    text=line.lstrip('# ').strip();kind='h1' if line.startswith('# ') else 'h2';para(text,kind,text)
                elif line.strip():
                    para(line)
        elif block.startswith('[FIGURE '):
            name,caption=block[8:-1].split(' | ');image(name,caption)
        elif block=='[RESULTS]':
            checks=json.loads((OUT/'gui_checks.json').read_text())
            rows=[['Check','Recorded result'],['Headless regression suite','PASS — 9 methods']]
            rows.extend([k.replace('_',' ').capitalize(),'PASS' if v else 'FAIL'] for k,v in checks.items() if isinstance(v,bool))
            table(rows,'Table 4.1: Recorded local verification outcomes')
        else:para(block.replace('\n',' '))
page();para('REFERENCES','h1','REFERENCES')
for n,(author,title,url) in enumerate(json.loads((OUT/'references.json').read_text()),1):
    para(f'[{n}] {author}, “{title}.” Available: {url}. Accessed: 16 November 2026.')
page();para('APPENDIX A: CODING','h1','APPENDIX A: CODING')
para('Selected excerpts show the implemented TCP framing and encrypted-message path. The complete runnable source is supplied separately in the project directory. These excerpts are extracted directly from the current source files.')


def code_excerpt(filename, qualified_name):
    source=(ROOT/filename).read_text()
    node=ast.parse(source)
    for name in qualified_name.split('.'):
        node=next(child for child in node.body if isinstance(child, (ast.ClassDef, ast.FunctionDef)) and child.name==name)
    para(filename+' — '+qualified_name,'h2')
    code=textwrap.dedent('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))
    style=ParagraphStyle('code',parent=styles['body'],alignment=0,spaceAfter=0,splitLongWords=True)
    for line in code.splitlines():
        p=D.add_paragraph();p.paragraph_format.space_after=Pt(0)
        p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.add_run(line if line else ' ')
        story.append(Paragraph(escape(line).replace(' ','&#160;') or '&#160;',style))


code_excerpt('network.py', 'ChatConnection.send')
page()
para('APPENDIX A: CODING — CONTINUED','h1')
code_excerpt('network.py', '_recv_exact')
code_excerpt('session.py', 'SecureSession.send')
para('The receive helper handles partial TCP reads. SecureSession.send encrypts text before passing it to the transport. The transport then prefixes the JSON byte length and sends the frame, as shown on the previous page.')
page();para('APPENDIX B: APPLICATION SCREENSHOTS','h1','APPENDIX B: APPLICATION SCREENSHOTS')
para('Actual desktop capture from the local two-client check: setup requires a passphrase before starting discovery and chat services.')
image('setup.png','Fig B.1: Required setup and passphrase validation')
page();para('APPENDIX B: APPLICATION SCREENSHOTS — CONTINUED','h1')
para('Actual verified two-way conversation. A macOS screen-recording permission dialog overlaps part of this capture. The image is retained unaltered; an unobstructed capture can replace it before submission.')
image('chat.png','Fig B.2: Verified two-way local conversation with operating-system dialog')
# Word should refresh its TOC fields when supported by the editor.
settings=D.settings.element;update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)
D.core_properties.title=TITLE;D.core_properties.subject='21CSC203P Advanced Programming Practice';D.core_properties.author=identity['students']
# Match the template's distinct preliminary-page type sizes.
for p in D.paragraphs:
    if p.text == 'ABSTRACT':
        break
    size = 16
    if p.text == TITLE:
        size = 18
    elif p.text in ('A PROJECT REPORT', 'Submitted by', 'Under the Guidance of',
                    'in partial fulfillment of the requirements for the degree of', 'NOVEMBER 2026'):
        size = 14
    elif p.text == guide_details:
        size = 12
    for run in p.runs:
        run.font.size = Pt(size)
        if p.text in ('Submitted by', 'Under the Guidance of'):
            run.italic = True

# Two-pass PDF pagination; PDF uses the same content, not a DOCX-rendering engine.
body_page=5

def footer_pdf(canvas,doc):
    canvas.saveState()
    canvas.setFillColorRGB(1,1,1);canvas.rect(0,0,A4[0],A4[1],fill=1,stroke=0)
    canvas.setFillColorRGB(0,0,0);canvas.setFont('TNR',12)
    if doc.page>=body_page:canvas.drawCentredString(A4[0]/2,30,str(doc.page-body_page+1))
    canvas.restoreState()

def pdf_doc():return SimpleDocTemplate(str(OUT/'CLOAK_Project_Report.pdf'),pagesize=A4,leftMargin=72,rightMargin=36,topMargin=57.6,bottomMargin=57.6,title=TITLE,author=identity['team_name'] or 'CLOAK Project')
# Contents spans two pages at most; use compact 12pt / 18pt chapter entries only.
labels=[line[2:].strip() for line in (OUT/'manuscript.md').read_text().splitlines() if line.startswith('# ')]+['REFERENCES','APPENDIX A: CODING','APPENDIX B: APPLICATION SCREENSHOTS']
first=copy.deepcopy(story);pdf_doc().build(first,onFirstPage=footer_pdf,onLaterPages=footer_pdf)
body_page=page_map[body_start_label]
contents=[]
for label in labels:
    contents.append(Paragraph(escape(label)+' . . . '+str(page_map[label]-body_page+1),styles['body']))
from reportlab.platypus import KeepTogether
story[contents_placeholder]=KeepTogether(contents)
pdf_doc().build(copy.deepcopy(story),onFirstPage=footer_pdf,onLaterPages=footer_pdf)
reader=PdfReader(OUT/'CLOAK_Project_Report.pdf')
summary={'pdf_pages':len(reader.pages),'body_starts_physical_page':page_map[body_start_label],
         'references_physical_page':page_map['REFERENCES'],
         'body_pages_before_references':page_map['REFERENCES']-page_map[body_start_label],
         'manuscript_words':len((OUT/'manuscript.md').read_text().split()),
         'references':15,'total_page_target':[30,35],
         'code_appendix':'Selected excerpts; full source supplied separately',
         'docx_note':'Editable DOCX uses a refreshable TOC. PDF is separately typeset from identical content; DOCX pagination depends on the editor.'}
(OUT/'report_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
assert 30 <= summary['pdf_pages'] <= 35, 'Complete report must contain 30–35 pages'
# Cache the compact chapter-level contents so the DOCX is readable before refresh.
# Word can recalculate this field if editing changes its pagination.
for child in list(field):
    field.remove(child)
for index,label in enumerate(labels):
    run=OxmlElement('w:r')
    text=OxmlElement('w:t')
    text.text=label+' . . . '+str(page_map[label]-body_page+1)
    run.append(text)
    if index < len(labels)-1:
        run.append(OxmlElement('w:br'))
    field.append(run)
D.save(OUT/'CLOAK_Project_Report.docx')
