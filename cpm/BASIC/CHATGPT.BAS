10 REM GPIO STRING READ/WRITE ROUTINES FOR SLAPI
20 REM USING MCP23017 GPIO EXPANDER
30 REM --------------------------------------------------

30 LEDUSER = 0 : REM USER LED write Opcode (0x00)
31 KEYUSER = 128 : REM USER KEY read Opcode (0x80)
32 GPPUA = 7 : REM GPPUA write Opcode (0x07)
33 IODIRA = 5 : REM IODIRA write Opcode (0x05)
34 GPIOAW = 3 : REM GPIOA write Opcode (0x03)
35 GPIOAR = 129 : REM GPIOA read Opcode (0x81)
36 REGDATAPORT = 0
37 REGSELPORT = 1
38 VALIDBIT = 16 : REM Bit 4
39 ACKBIT = 32   : REM Bit 5
40 SOH = 1
41 SOT = 2
42 EOT = 4
43 QT$ = CHR$(34)
44 BSLASH = 92
45 CRLF$ = CHR$(13) + CHR$(10)
50 OPEN "I", #1, "KEY" : INPUT #1, KEY$
55 PRINT "Key = " + LEFT$(KEY$, 4); "..."; RIGHT$(KEY$, 4)
60 CLOSE #1
65 MASK = 0

70 GOSUB 600 : REM Read string over GPIOA should be slapi ready header

105 S$="DOMAIN api.openai.com" + CRLF$ : GOSUB 800 : REM Send domain command to slapi
106 GOSUB 600 : REM Read OK response from slapi
110 S$="HTTPS" + CRLF$ : GOSUB 800 : REM Send protocol command to slapi
111 GOSUB 600 : REM Read OK response from slapi
120 S$="HEADERS Content-Type application/json" + CRLF$ : GOSUB 800 : REM Send header to slapi
121 GOSUB 600 : REM Read OK response from slapi
130 S$="RESPONSE HDRS_OFF" + CRLF$ : GOSUB 800 : REM Send hdrs off command to slapi
131 GOSUB 600 : REM Read OK response from slapi

139 REM KEY is max string len so we must send the header as pieces
140 S$="HEADERS Authorization Bearer " : GOSUB 800 : REM Send auth header to slapi
141 MASK = 1
142 S$ = KEY$ : GOSUB 800 : REM Send key as part of auth header
143 MASK = 0
144 S$ = CRLF$ : GOSUB 800 : REM Send CRLF to finish auth header
145 GOSUB 600 : REM Read OK response from slapi

150 S$="RESPONSE JSONPATH $.data[1].id" + CRLF$ : GOSUB 800 : REM Send JSON path command to slapi
151 GOSUB 600 : REM Read OK response from slapi

160 S$="GET /v1/models HTTP/1.1" + CRLF$ + CRLF$: GOSUB 800 : REM Send GET command to slapi
161 GOSUB 8000 : REM Wait a bit
162 WAITCHAR = EOT : GOSUB 500 : REM Wait for end of transmission character from slapi

170 S$="RESPONSE JSONPATH $.output[1].content[0].text" + CRLF$ : GOSUB 800 : REM Send JSON path command to slapi to extract text of first choice in response
171 GOSUB 600 : REM Read OK response from slapi

240 REM CHAT LOOP - INPUT STRING TO SEND TO CHATGPT, SEND IT, THEN READ AND PRINT RESPONSE
250 LINE INPUT ">"; T$
260 S$="POST /v1/responses HTTP/1.1" + CRLF$ + CRLF$ + "{ " + QT$ + "model" + QT$ + ": " + QT$ + "gpt-5-nano" + QT$ + ", " + QT$ + "input" + QT$ + ": " + QT$ : GOSUB 800
270 S$=T$ : GOSUB 800
280 S$ = QT$ + "}" + CRLF$ + CRLF$ : GOSUB 800
290 GOSUB 8000 : REM Wait a bit
300 WAITCHAR = EOT : GOSUB 500 : REM Wait for end of transmission character from slapi
310 GOTO 240 : REM Loop back to allow sending another string

500 REM READ UNTIL A SPECIFIC CHARACTER OVER GPIO - WAITCHAR
510 GOSUB 9500 : REM Set gpio for input
512 BS=0
515 PRINT "<= ";
520 C=0 : GOSUB 1000 : REM Read high nibble
530 C=(NB*16) : GOSUB 1000 : REM Read low nibble
540 C=C+NB : REM Combine nibbles
545 IF C=WAITCHAR THEN 590
550 IF BS=0 THEN 570 ELSE GOSUB 7000 : REM Print a control character in C
560 BS=0 : GOTO 520
570 IF C=BSLASH THEN BS=1 ELSE GOSUB 6900 : REM Print a character in C
580 GOTO 520
590 RETURN

600 REM READ A STRING OVER GPIO USE 0-3 AS DATA PINS 4 as valid and 5 as ack
610 GOSUB 9500 : REM Set gpio for input
620 PRINT "<= ";
681 GOTCR=0
682 GOTCRLF=0
683 LINELEN=0
685 C=0
690 WHILE GOTCRLF=0 : REM Loop until carriage return
700 GOSUB 1000 : REM Read high nibble
705 C=(NB*16)
710 GOSUB 1000 : REM Read low nibble
720 C=C+NB : REM Combine nibbles
730 IF ((C >=32) AND (C <=126)) OR (C=10) OR (C=13) THEN PRINT CHR$(C);
731 LINELEN=LINELEN+1
733 IF GOTCR=1 AND C=10 THEN GOTCRLF=1 ELSE GOTCR=0 : REM Check for line feed after carriage return
735 IF C=13 THEN GOTCR=1 : REM Check for carriage return
740 WEND
760 RETURN

800 REM SEND A STRING OVER GPIO USE 0-3 AS DATA PINS 4 as valid and read 5 as ack
810 REM Send high nibble first, string is s$
815 PRINT "=> "; 
816 IF MASK=0 THEN PRINT s$ ELSE PRINT "****"; : REM Print string to send, or mask if it is secret
820 GOSUB 9600 : REM Set GPIO for output
880 FOR I=1 TO LEN(s$)
890 C=ASC(MID$(s$,I,1))
900 NB=(C AND 240)/16
920 GOSUB 2100 : REM Send high nibble
925 NB=C AND 15
930 GOSUB 2100 : REM Send low nibble
940 NEXT I
950 RETURN

1000 REM * * * * * READ NIBBLE
1005 GOSUB 9350 : REM Clear ack bit
1045 GOSUB 9000 : REM Wait for valid set
1065 GOSUB 9450 : REM Read data bits
1075 GOSUB 9300 : REM Set ack bit
1110 GOSUB 9350 : REM Clear ack bit
1120 RETURN

2100 REM * * * * * SEND NIBBLE
2120 GOSUB 9400 : REM Output nibble to GPIOAW data pins
2130 GOSUB 9100 : REM Set valid bit
2140 GOSUB 9200 : REM Wait for ack set
2150 GOSUB 9150 : REM Clear valid bit 
2160 GOSUB 9250 : REM Wait for ack release
2170 RETURN

6900 REM Print a character in C
6910 IF ((C>=32) AND (C<=126)) OR (C=13) THEN PRINT CHR$(C);
6920 IF C=10 THEN PRINT "" : REM Line feed
6930 RETURN

7000 REM Print a control character in C
7010 IF C=110 THEN PRINT "" : RETURN : REM Line feed
7015 IF C=114 THEN PRINT CHR$(13); : RETURN : REM Carriage return
7020 IF C=116 THEN PRINT CHR$(9); : RETURN : REM Tab
7030 IF C=92 THEN PRINT CHR$(92); : RETURN : REM Backslash
7040 IF C=34 THEN PRINT CHR$(34); : RETURN : REM Quote
7090 PRINT "?"; : RETURN

8000 REM Wait a bit 
8010 FOR I = 1 TO 6000 : NEXT I
8020 RETURN 

8900 REM ***** GPIO FNS - REWRITE THESE FOR YOUR SBC *****

9000 REM Wait for valid set
9010 VALID = 0 : WHILE (VALID = 0) : OUT REGSELPORT, GPIOAR : VALID = INP(REGDATAPORT) AND VALIDBIT : WEND
9020 RETURN

9050 REM Wait for valid clear
9060 VALID = VALIDBIT : WHILE (VALID<>0) : OUT REGSELPORT, GPIOAR : VALID = INP(REGDATAPORT) AND VALIDBIT : WEND
9070 RETURN

9100 REM Set Valid
9110 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, NB OR VALIDBIT
9120 RETURN

9150 REM Clear Valid
9160 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, NB
9170 RETURN

9200 REM Wait for ack set
9210 ACK = 0 : WHILE (ACK = 0) : OUT REGSELPORT, GPIOAR : ACK = INP(REGDATAPORT) AND ACKBIT : WEND
9220 RETURN

9250 REM Wait for ack clear
9260 ACK = ACKBIT : WHILE (ACK<>0) : OUT REGSELPORT, GPIOAR : ACK = INP(REGDATAPORT) AND ACKBIT : WEND
9270 RETURN

9300 REM Set Ack
9310 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, NB OR ACKBIT
9320 RETURN

9350 REM Clear Ack
9360 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, NB
9370 RETURN

9400 REM Output nibble to GPIOAW data pins
9410 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, NB 
9420 RETURN

9450 REM Read nibble from GPIOAW data pins
9460 OUT REGSELPORT, GPIOAR : NB=INP(REGDATAPORT) AND 15
9470 RETURN

9500 REM Set GPIO for input
9510 REM  MCP23017 GPIOA pins (IODIRA=0x1F) used as:
9520 REM   0-3 : data bits (input)
9530 REM     4 : valid bit (input)
9540 REM     5 : ack bit (output)
9545 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, 0  : REM Clear MCP23017 GPIOAW port
9550 OUT REGSELPORT, IODIRA : OUT REGDATAPORT, 223 : REM Set MCP23017 GPIOAW 0-3 as input, 4 as input, 5 as output
9560 OUT REGSELPORT, GPPUA : OUT REGDATAPORT, 0 : REM Disable pull-ups on GPIOAW
9570 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, 0  : REM Clear MCP23017 GPIOAW port
9580 RETURN

9600 REM Set GPIO for output
9610 REM  MCP23017 GPIOA pins (IODIRA=0x20) used as:
9620 REM   0-3 : data bits (output)
9630 REM     4 : valid bit (output)
9640 REM     5 : ack bit (input)
9650 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, 0  : REM Clear MCP23017 GPIOAW port
9660 OUT REGSELPORT, IODIRA : OUT REGDATAPORT, 32 : REM Set MCP23017 GPIOA 0-3 and 4 as output, 5 as input
9670 OUT REGSELPORT, GPPUA : OUT REGDATAPORT, 0 : REM Disable pull-ups on GPIOAW
9680 OUT REGSELPORT, GPIOAW : OUT REGDATAPORT, 0  : REM Clear MCP23017 GPIOAW port
9690 RETURN

