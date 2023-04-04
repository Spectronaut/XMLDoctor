import os
import datetime
import tkinter
import tkinter.filedialog
import tempfile
import xml.dom.minidom
import xml.etree.ElementTree as ET
from tkinter.constants import ANCHOR, BOTTOM, DISABLED, E, END, LEFT, N, NO, RIGHT, S, W, X, Y
from tkinter.scrolledtext import *
from tkinter.filedialog import asksaveasfile
from lxml import etree

# global variables
global xsd_file_path

# Variables
# set time and logfile location for log
dt = datetime.datetime.now()
date_time = dt.strftime("%m/%d/%Y, %H:%M:%S")
date_log = dt.strftime("%m%d%Y")
home_directory = os.path.expanduser( '~' )
log_path = f"{home_directory}/XMLlogs/" 
logFile = f"{date_log}.txt"   

if not os.path.exists(f"{log_path}"):
    os.makedirs(log_path)
    with open(f"{log_path}{logFile}", "w+"):
        pass

class Validator:
    def __init__(self, xsd_path: str):
        xmlschema_doc = etree.parse(xsd_path)
        self.xmlschema = etree.XMLSchema(xmlschema_doc)

    def validate(self, xml_path: str):
        global validator_error_msg
        validator_error_msg = ""
        try:
            xml_doc = etree.parse(xml_path)
            result = self.xmlschema.validate(xml_doc)
            try:
                self.xmlschema.assert_(xml_doc)
            except Exception as assertion_error:
                validator_error_msg = "ERROR : " + str(assertion_error)
        except etree.ParseError as e:
            validator_error_msg = 'ERROR : '+str(e.msg)
            result = False
        return result   

class Transform:
    def __init__(self, xsl_file_path: str):
        xsltransform_doc = etree.parse(xsl_file_path)
        self.xmlschema = etree.XSLT(xsltransform_doc)

    def transform_this(self, xslt_src_path: str):
        global xsl_transform_msg
        xsl_transform_msg = ""
        try:
            xml_doc = etree.parse(xslt_src_path)
            tempresult = self.xmlschema(xml_doc)
            result = etree.tostring(tempresult, pretty_print=True)
        except etree.ParseError as e:
            result = 'ERROR : '+str(e.msg)
        return result   
    
class TextLineNumbers(tkinter.Canvas):
    def __init__(self, *args, **kwargs):
        tkinter.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget
        
    def redraw(self, *args):
        '''redraw line numbers'''
        self.delete("all")

        i = self.textwidget.index("@0,0")
        while True :
            dline= self.textwidget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2,y,anchor="nw", text=linenum)
            i = self.textwidget.index("%s+1line" % i)

class CustomText(tkinter.Text):
    def __init__(self, *args, **kwargs):
        tkinter.Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        # let the actual widget perform the requested action
        cmd = (self._orig,) + args
        # the next try catch prevent a crash from a paste event 
        # apparently, the problem is that when you paste there is nothing selected and that
        # breaks this 
        try:
            result = self.tk.call(cmd)
        except Exception:
            return None

        # generate an event if something was added or deleted,
        # or the cursor position changed
        if (args[0] in ("insert", "replace", "delete") or 
            args[0:3] == ("mark", "set", "insert") or
            args[0:2] == ("xview", "moveto") or
            args[0:2] == ("xview", "scroll") or
            args[0:2] == ("yview", "moveto") or
            args[0:2] == ("yview", "scroll")
        ):
            self.event_generate("<<Change>>", when="tail")

        # return what the actual widget returned
        return result       
                
class TextboxLineNumbers(tkinter.Frame):
    def __init__(self, *args, **kwargs):
        tkinter.Frame.__init__(self, *args, **kwargs)
        try:
            self.text = CustomText(self)
        except Exception as e:
            insertToMsgBox(str(e))
        self.vsb = tkinter.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set, selectbackground="yellow", selectforeground="black", undo=True, width=1000, height=35)
        self.text.tag_configure("bigfont", font=("Helvetica", "20", "bold"))
        self.linenumbers = TextLineNumbers(self, width=30)
        self.linenumbers.attach(self.text)

        self.vsb.pack(side="right", fill="y")
        self.linenumbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)

        self.text.bind("<<Change>>", self._combined_onChange_Highlight)
        self.text.bind("<Configure>", self._on_change)
        self.text.tag_configure('tag', foreground='blue')
        self.text.tag_configure('attribute', foreground='green')
        self.text.tag_configure('value', foreground='purple')  

    def _combined_onChange_Highlight(self, event):   
        self._on_change(event)
        self.highlight_xml(event)    
            
    def _on_change(self, event):
        self.linenumbers.redraw()

    # syntax highliting happens here
    def highlight_xml(self,event=None):
        # remove all existing tags
        self.text.tag_remove('tag', '1.0', tkinter.END)
        self.text.tag_remove('attribute', '1.0', tkinter.END)
        self.text.tag_remove('value', '1.0', tkinter.END)

        # get the XML input and split it into lines
        xml_input = self.text.get('1.0', tkinter.END)
        lines = xml_input.splitlines()

        # iterate over the lines and highlight syntax
        for i, line in enumerate(lines):
            j = 0
            while j < len(line):
                # highlight tags
                tag_start = line.find('<', j)
                if tag_start != -1:
                    tag_end = line.find('>', tag_start)
                    if tag_end != -1:
                        self.text.tag_add('tag', f'{i+1}.{tag_start}', f'{i+1}.{tag_end+1}')
                        j = tag_end + 1
                    else:
                        break
                else:
                    break

                # highlight attributes
                attr_start = line.find(' ', tag_start, tag_end)
                while attr_start != -1:
                    attr_end = line.find('=', attr_start, tag_end)
                    if attr_end != -1:
                        self.text.tag_add('attribute', f'{i+1}.{attr_start}', f'{i+1}.{attr_end}')
                        value_start = line.find('"', attr_end, tag_end)
                        if value_start != -1:
                            value_end = line.find('"', value_start+1, tag_end)
                            if value_end != -1:
                                self.text.tag_add('value', f'{i+1}.{value_start}', f'{i+1}.{value_end+1}')
                                j = value_end + 1
                            else:
                                break
                        else:
                            break
                    else:
                        break
                    attr_start = line.find(' ', attr_end, tag_end)

                # move to the next character
                j += 1
                        
    def validate_XSD(self):
        # in order to validate in session we need to call a file path, 
        # to do this save the file to a temp location with a temp name and 
        # validate the temp xml file.
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmpfile:
            try:
                if xsd_file_path == "":
                    insertToMsgBox("No XSD")
                else:
                    file = self.text.get(1.0, END)
                    tmpfile.write(file.encode())
                    # no idea why this was needed but in some computers you dont need this ???
                    tmpfile.flush()                    
                    validator = Validator(xsd_file_path)
                    validate_result = validator.validate(tmpfile.name)
                    
                    if not validate_result:
                        insertToMsgBox(validator_error_msg)
                    else:
                        insertToMsgBox("Validated!")
                    tmpfile.close()
                    os.remove(tmpfile.name)
            except Exception as e:
                tmpfile.close()
                os.remove(tmpfile.name)
                insertToMsgBox("No XSD")

    def transform_current_xml(self):
            # in order to validate in session we need to call a file path, 
            # to do this save the file to a temp location with a temp name and 
            # validate the temp xml file.
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmpfile:
                try:
                    if xsl_file_path == "":
                        insertToMsgBox("No XSL")
                    else:
                        file = self.text.get(1.0, END)
                        tmpfile.write(file.encode())
                        # no idea why this was needed but in some computers you dont need this ???
                        tmpfile.flush()                        
                        transform = Transform(xsl_file_path)
                        transform_result = transform.transform_this(tmpfile.name)
                        insertToMsgBox(f"Transformed!")
                        self.text.delete('1.0', END)
                        self.text.insert("end",transform_result)
                        tmpfile.close()
                        os.remove(tmpfile.name)
                except Exception as e:
                    tmpfile.close()
                    os.remove(tmpfile.name)
                    insertToMsgBox("No XSL")

    def validate_XML(self):
                # in order to validate in session we need to call a file path, 
                # to do this save the file to a temp location with a temp name and 
                # validate the temp xml file.
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmpfile:
                    try:
                        src_xml = self.text.get(1.0, END)
                        if src_xml == "":
                            insertToMsgBox("Nothing to validate")
                        else:
                            file = self.text.get(1.0, END)
                            tmpfile.write(file.encode())
                            # no idea why this was needed but in some computers you dont need this ???
                            tmpfile.flush()                            
                            tree = ET.parse(tmpfile.name)
                    except Exception as e:
                        tmpfile.close()
                        os.remove(tmpfile.name)
                        insertToMsgBox(str(e))
                    else:
                        insertToMsgBox(f"XML is valid!")
                        tmpfile.close()
                        os.remove(tmpfile.name)         

    def get_path(self): 
        try:
            # clean the text widget before loading the next file
            directoryname = tkinter.filedialog.askopenfile()
            self.xml_file_name = directoryname.name
            self.xml_file_path = self.xml_file_name
            text_file = open(self.xml_file_name, 'r')
            content = text_file.read()
            insertToMsgBox(f"Loading... {directoryname.name}")
            self.text.delete('1.0', END)
            self.text.insert("end",content)
            editwindow.title(f"XMLDoctor - {directoryname.name}")
        except Exception as e:
            insertToMsgBox(str(e))
        return directoryname.name

    def make_pretty(self): 
        try:
            # clean the text widget before loading the next file
            tempfile = xml.dom.minidom.parseString(self.text.get(1.0, END))
            xmlstring = tempfile.toprettyxml(newl='\r\n')
            content = xmlstring
            insertToMsgBox(f"Prettified!")
            self.text.delete('1.0', END)
            self.text.insert("end",content)
        except Exception as e:
            insertToMsgBox(str(e))

    def save(self):
        try:  
            text_file = open(self.xml_file_path, 'w')
            text_file.write(self.text.get(1.0, END))
            text_file.close()
            text_file = open(self.xml_file_path, 'r')
            insertToMsgBox(f"{self.xml_file_path} Saved!")
        except Exception as e:
            insertToMsgBox(str(e))

    def saveAs(self):
        try:  
            f = asksaveasfile(initialfile = 'Untitled.xml', defaultextension=".xml", filetypes=[("All Files","*.*"),("XML Document","*.xml")])
            text_file = open(f.name, 'w')
            text_file.write(self.text.get(1.0, END))
            text_file.close()
            text_file = open(f.name, 'r')
            insertToMsgBox(f"{f.name} Saved!")
        except Exception as e:
            insertToMsgBox(str(e))

def set_XSD_path():
    try:
        global xsd_file_path
        XSDpath = tkinter.filedialog.askopenfile()
        xsd_file_path = XSDpath.name
        validator = Validator(xsd_file_path)
        XSD_status_bar.config(text= f"Current XSD File - {xsd_file_path}")
        return xsd_file_path
    except Exception as e:
        insertToMsgBox("Please select a valid XSD File")

def set_XSL_path():
    try:
        global xsl_file_path
        XSLPath = tkinter.filedialog.askopenfile()
        xsl_file_path = XSLPath.name
        transform = Transform(xsl_file_path)
        XSL_status_bar.config(text= f"Current XSL File - {xsl_file_path}")
        return xsl_file_path   
    except Exception as e:
        insertToMsgBox("Please select a valid XSL File")

def insertToMsgBox(msg):
    now = datetime.datetime.now()
    msg = f"{now} - {msg} \n"
    text_box.insert("end", msg)
    text_box.pack(side=BOTTOM)
    text_box.see(tkinter.END)  
    with open(f'{log_path}{logFile}', 'a') as log_file:
        log_string = ''.join(map(str,msg))
        log_file.write(log_string)
    
editwindow = tkinter.Tk()
editwindow.title("XMLDoctor")
editwindow.resizable(width=True, height=True)
editwindow.geometry("800x800")

# XML Editor Text Frame
editor_frame = tkinter.Frame(editwindow)
editor_frame.pack(pady=5)

# XML Editor Text Window
editor_text = TextboxLineNumbers(editor_frame)
editor_text.pack()

# Buttons frame
btn_frame = tkinter.Frame(editwindow)
btn_frame.pack()

# Buttons
save_btn = tkinter.Button(btn_frame, text="Save",command=editor_text.save)
save_btn.grid(row=0,column=0,padx=10)

saveAs_btn = tkinter.Button(btn_frame, text="Save As...",command=editor_text.saveAs)
saveAs_btn.grid(row=0,column=1,padx=10)

open_btn = tkinter.Button(btn_frame, text="Open",command=editor_text.get_path)
open_btn.grid(row=0,column=2,padx=10)

transform_btn = tkinter.Button(btn_frame, text="Transform XSL",command=editor_text.transform_current_xml)
transform_btn.grid(row=0,column=3,padx=10)

XMLvalidate_btn = tkinter.Button(btn_frame, text="Validate XSD",command=editor_text.validate_XSD)
XMLvalidate_btn.grid(row=0,column=4,padx=10)

validate_btn = tkinter.Button(btn_frame, text="Sanitize XML",command=editor_text.validate_XML)
validate_btn.grid(row=0,column=5,padx=10)

make_pretty_btn = tkinter.Button(btn_frame, text="Format XML",command=editor_text.make_pretty)
make_pretty_btn.grid(row=0,column=6,padx=10)

# init the console text widget
text_box = ScrolledText(editwindow, width=1000, height=100, wrap='word')

# status bar frame
statusxsd_frame = tkinter.Frame(editwindow)
statusxsd_frame.pack(side=BOTTOM, anchor=W)
statusxsl_frame = tkinter.Frame(editwindow)
statusxsl_frame.pack(side=BOTTOM, anchor=W)

# Current XSD Status bar
XSD_status_bar = tkinter.Label(statusxsd_frame, text='No XSD File Selected...', anchor=W, wraplength=10000)
XSD_status_bar.pack(fill=X,side=LEFT, ipadx=5, ipady= 5)
openXSD_btn = tkinter.Button(statusxsd_frame, text="Select XSD File",command=set_XSD_path)
openXSD_btn.pack(fill=X,side=RIGHT)

# Current XSL Status bar
XSL_status_bar = tkinter.Label(statusxsl_frame,text='No XSL File Selected...', anchor=W, wraplength=10000)
XSL_status_bar.pack(fill=X,side=LEFT, ipadx=5, ipady= 5)
openXSL_btn = tkinter.Button(statusxsl_frame, text="Select XSl File",command=set_XSL_path)
openXSL_btn.pack(fill=X,side=RIGHT)

# call functions at runtime 
insertToMsgBox("Welcome")

# run the darn thing
editwindow.mainloop()
