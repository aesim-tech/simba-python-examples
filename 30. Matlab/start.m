%if you encounter some issues with tcl initialisation inside matlab, please run this script "start.m"
%But you need to modify the path of tcl8.6 and tk8.6 in accordance to your computer (from Python installation folder)
%setenv('TCL_LIBRARY', 'X:\XXX\tcl\tcl8.6');
%setenv('TK_LIBRARY', 'X:\XXXX\tcl\tk8.6');
%py.tkinter.Tk;

setenv('TCL_LIBRARY', 'C:\Users\amc\AppData\Local\Programs\Python\Python310\tcl\tcl8.6');
setenv('TK_LIBRARY', 'C:\Users\amc\AppData\Local\Programs\Python\Python310\tcl\tk8.6');
py.tkinter.Tk;