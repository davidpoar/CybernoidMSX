# Spectrum ROM Disassembly - Preface and Introduction

---

@owfetetc 

SPECTRUM 

ROM 

DISASSEMBLY 


BY 

Dr Ian Logan & Dr Frank O’Hara 


Transcribed by the following readers of 
the comp.sys.sinclair newsgroup:- 

J.R. Biesma 
Biggo 

Dr. J. Bland 
Paul E .Collins 
Chris Cowley 
Dr. Rupert Goodwins 
Jonathan G Harston 
Marcus Lund 
Joe Mackay 
Russell Marks 
Eduardo Yanez Parareda 
Adam Stonehewer 
Mark Street 
Gerard Sweeney 
Geoff Wearmouth 
Matthew Westcott 
Matthew Wilson 
Witchy 


1 



Preface 


The Sinclair ZX Spectrum is a worthy successor to the ZX 81 which in turn replaced the ZX 80. 

The Spectrum has a 1 6K monitor program. This program has been developed directly from the 4K program 
of the ZX 80 although there are now so many new features that the differences outweigh the similarities. 

We have both enjoyed producing this book. We have learnt a great deal about the techniques of Z80 
machine code programming and now feel that between us we have unravelled the ‘secrets of the Spectrum’. 

We would like to thank: 

- Our families. 

- Alfred Milgrom, our publisher who has been extremely helpful. 

- Philip Mitchell whose notes on the cassette format were most informative. 

- Clive Sinclair and his team at Sinclair Research Ltd. who have produced such a ‘challenging’ and 
useful machine. 

January 1983 

Ian Logan Lincoln, U.K. 

Frank O’Hara London, U.K. 


2 



Contents 


page 

Preface 

Introduction 

The DISASSEMBLY 

The restart routines and tables 1 

The keyboard routines 5 

The loudspeaker routines 11 

The cassette handling routines 15 

The screen and printer handling routines 33 

The executive routines 59 

BASIC line and command interpretation 84 

Expression evaluation 127 

The arithmetic routines 164 

The floating-point calculator 190 

Appendix 

BASIC programs for the main series 222 

(SINX, EXP X, LNX&ATN X) 

- The ‘DRAW’ algorithm 228 

The ‘CIRCLE’ algorithm 228 

Note on small integers and -65536 229 

Index to routines 231 


3 



Introduction 


The 16K monitor program of the Spectrum is a complex Z80 machine code program. Its overall structure is very clear in that it is divided 
into three major parts: 

a. Input/Output routines 

b. BASIC interpreter 

c. Expression handling 

However these blocks are too large to be managed easily and in this book the monitor program is discussed in ten parts. 

Each of these parts will now be ‘outlined’. 

The restart routines and tables. 

At the start of the monitor program are the various ‘restart’ routines that are called with the single byte RST’ instructions. All of the 
restarts are used. For example 'restart 0008’ is used for the reporting of syntax or run-time errors. 

The tables in this part of the monitor program hold the expanded forms of the tokens and the ‘key-codes’. 

The keyboard routine. 

The keyboard is scanned every 1/50 th. of a second (U.K. model) and the keyboard routine returns the required character code. All of 
the keys of the keyboard 'repeat' if they are held down and the keyboard routine takes this into consideration. 

The loudspeaker routines. 

The spectrum has a single on-board loudspeaker and a note is produced by repeatedly using the appropriate 'OUT' instruction. In the 
controller routine great care has been taken to ensure that the note is held at a given 'pitch' throughout its 'duration'. 

The cassette handling routines. 

It was a very unfortunate feature of the ZX 81 that so little of the monitor program for that machine was devoted to the cassette 
handling. 

However in the Spectrum there is an extensive block of code and now the high standard of cassette handling is one of the most 
successful features of the machine. 

BASIC programs or blocks of data are both dealt with in the same manner of having a 'header' block (seventeen bytes) that is SAVEd 
first. This 'header' describes the 'data block' that is SAVEd after it. 

One disadvantage of this system is that it is not possible to produce programs with any 'security' whatsoever. 

The screen and printer handling routines. 

All of the remaining input/output routines of the Spectrum are 'vectored' through the 'channel & stream information areas'. 

In the standard Spectrum 'input' is only possible from the keyboard but 'output' can be directed to the printer, the upper part of the T.V. 
display or the lower part of the T.V. display. 

The major 'input' routine in this part of the monitor program is the EDITOR that allows the user to enter characters into the lower part of 
the T.V. display. 

The PRINT-OUT routine is a rather slow routine as the same routine is used for 'all possibilities'. For example, the adding of a single 
byte to the 'display area' involves considering the present status of OVER and INVERSE on every occasion. 

The executive routines 

In this part of the monitor program are to be found the INITIALISATION procedure and the 'main execution loop' of the BASIC 
interpreter. 

In the Spectrum the BASIC line returned by the EDITOR is checked for the correctness of its syntax and then saved in the program 
area, if it was a line starting with a line number, or 'executed' otherwise. 

This execution can in turn lead to further statements being considered. (Most clearly seen as in the case of - RUN.) 



BASIC line and command interpretation. 

This part of the monitor program considers a BASIC line as a set of statements and in its turn each statement as starting with a 
particular command. For each command there is a 'command routine' and it is the execution of the machine code in the appropriate 
'command routine' that effects the 'interpretation'. 

Expression evaluation 

The Spectrum has a most comprehensive expression evaluator allowing for a wide range of variable types, functions and operations. 
Once again this part of the monitor is fairly slow as all the possible alternatives have to be considered. 

The handling of strings is particularly well managed. All simple strings are managed 'dynamically' and old copies are 'reclaimed' once 
they are redundant. This means that there is no ’garbage collecting' to be done. 

The arithmetic routines 

The Spectrum has two forms for numbers. Integer values in the range -65535 to +65535 are in an 'integral' or 'short' form whilst all other 
numbers are in a five byte floating point form. 

The present version of the monitor is unfortunately marred by two mistakes in this part. 

i. There is a mistake in 'division' whereby the 34th bit of a division is lost. 

ii. The value of -65536 is sometimes put in 'short' form and at other times in 'floating-point' and this leads to troubles. 

The floating-point calculator 

The CALCULATOR of the Spectrum handles numbers and strings and its operations are specified by ’literals'. It can therefore be 
considered that there is an internal 'stack operating' language in the CALCULATOR. 

This part of the monitor program contains routines for all the mathematical functions. The approximations to SIN X, EXP X, LN X & ATN 
X are obtained by developing Chebyshev polynomials and full details are given in the appendix. 

Overall the 16K monitor program offers an extremely wide range of different BASIC commands and functions. The programmers have 
always however been short of 'room' and hence the program is written for 'compactness' rather than 'speed'. 



THE DISASSEMBLY 

