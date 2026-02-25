; chatgpt.asm - Z80 CP/M 2.2 version of BASIC/CHATGPT.bas
; GPIO string read/write routines for SLAPI using MCP23017 GPIO expander.

            ORG     100h
            JP      START

; -----------------------------
; Constants
; -----------------------------
GPPUA       EQU     07h
IODIRA      EQU     05h
GPIOAW      EQU     03h
GPIOAR      EQU     81h

REGDATAPORT EQU     00h
REGSELPORT  EQU     01h

VALIDBIT    EQU     10h
ACKBIT      EQU     20h

EOT         EQU     04h
BSLASH      EQU     5Ch

BDOS        EQU     0005h
MAXLEN      EQU     250

; -----------------------------
; Program start
; -----------------------------
START:
            LD      HL, 0000h
            ADD     HL, SP
            LD      (OLD_STACK), HL
            LD      HL, STACK_END
            LD      SP, HL

            LD      DE,STR_INTRO
            CALL    PRINT_Z

            CALL    GPIO_SET_INPUT               ; first time dont hold for valid as may already be set by SLAPI;
            CALL    READ_STRING_INP              ; SLAPI ready header

            LD      DE,STR_DOMAIN
            CALL    SEND_Z
            CALL    READ_STRING

            LD      DE,STR_HTTPS
            CALL    SEND_Z
            CALL    READ_STRING

            LD      DE,STR_HDR_JSON
            CALL    SEND_Z
            CALL    READ_STRING

            LD      DE,STR_HDRS_OFF
            CALL    SEND_Z
            CALL    READ_STRING

            LD      DE,STR_AUTH
            CALL    SEND_Z
            CALL    READ_STRING

            LD      DE,STR_JSONPATH_CHAT
            CALL    SEND_Z
            CALL    READ_STRING

CHAT_LOOP:
            LD      DE,STR_PROMPT
            CALL    PRINT_Z

            CALL    READ_LINE                       ; DE=buffer, null terminated
            LD      DE,STR_CRLF
            CALL    PRINT_Z

            LD      DE,INBUF_DATA
            LD      HL,STR_QUIT
            CALL    STR_CMP
            JR      Z,END

            CALL    GPIO_OUTPUT
            LD      DE,STR_POST_START
            CALL    SEND_Z_OUT
            LD      DE,INBUF_DATA
            CALL    SEND_Z_OUT                      ; send user input, dont reset interface
            LD      DE,STR_POST_END
            CALL    SEND_Z_OUT                      ; send post end, dont reset interface

            LD      DE,STR_CRLF
            CALL    PRINT_Z

            CALL    DELAY_SHORT
            LD      A,EOT
            CALL    WAIT_FOR_CHAR
            JP      CHAT_LOOP


END:        LD      HL,(OLD_STACK)
            LD      SP, HL
            RET                                         ; return to CP/M
; -----------------------------
; Console routines
; -----------------------------
PRINT_Z:    ; DE -> zero-terminated string
            PUSH    DE
.PZ_LOOP:
            LD      A,(DE)
            OR      A
            JR      Z,.PZ_DONE
            CALL    CON_OUT
            INC     DE
            JR      .PZ_LOOP
.PZ_DONE:
            POP     DE
            RET

CON_OUT:    ; A -> console char
            PUSH    AF
            PUSH    BC
            PUSH    DE
            PUSH    HL
            LD      E,A
            LD      C,02h
            CALL    BDOS
            POP     HL
            POP     DE
            POP     BC
            POP     AF
            RET

READ_LINE:  ; returns DE -> null terminated text
            LD      B, MAXLEN
            LD      HL,INBUF_DATA
.RL_LOOP:
            LD      (HL),0              ; clear the buffer to zeros
            INC     HL
            DJNZ     .RL_LOOP
            LD      DE,INBUF
            LD      C,0Ah               ; BDOS read console string
            CALL    BDOS
            LD      DE,INBUF_DATA       ; point DE to start of string
            RET

PRINT_ESCAPED:
            LD      A,(BSFLAG)
            OR      A
            JR      Z,.PE_NORMAL
            XOR     A
            LD      (BSFLAG),A
            LD      A,B
            CP      'n'
            JR      NZ,.PE_CHK_R
            LD      A,0Dh
            CALL    CON_OUT
            LD      A,0Ah
            CALL    CON_OUT
            RET
.PE_CHK_R:
            CP      'r'
            JR      NZ,.PE_CHK_T
            LD      A,0Dh
            CALL    CON_OUT
            RET
.PE_CHK_T:
            CP      't'
            JR      NZ,.PE_CHK_BS
            LD      A,09h
            CALL    CON_OUT
            RET
.PE_CHK_BS:
            CP      '\'
            JR      NZ,.PE_CHK_Q
            LD      A,'\'
            CALL    CON_OUT
            RET
.PE_CHK_Q:
            CP      '"'
            JR      NZ,.PE_QMARK
            LD      A,'"'
            CALL    CON_OUT
            RET
.PE_QMARK:
            LD      A,'?'
            CALL    CON_OUT
            RET

.PE_NORMAL:
            LD      A,B
            CP      BSLASH
            JR      NZ,.PE_PRINT
            LD      A,01h
            LD      (BSFLAG),A
            RET

.PE_PRINT:
            LD      A,B            
            CP      0Dh
            JR      Z,.PE_CONOUT
            CP      0Ah
            JR      Z,.PE_CONOUT
            CP      20h
            JR      C,.PE_DONE
            CP      7Fh
            JR      NC,.PE_DONE
.PE_CONOUT:
            CALL    CON_OUT
            RET
.PE_DONE:
            RET

PRINT_HEX:                              ; Print the value in A as two hex digits
            PUSH    AF
            PUSH    BC
            LD      B,A
            LD      A,'x'
            CALL    CON_OUT
            LD      A,B
            SRL     A
            SRL     A
            SRL     A
            SRL     A
            CALL    PRINT_DIGIT
            LD      A,B
            CALL    PRINT_DIGIT
            POP     BC
            POP     AF
            RET

PRINT_DIGIT:
            AND     0Fh                 ; isolate low nibble
            CP      0Ah
            JR      C,.PD_DIGIT
            ADD     A,'A'-10            ; convert to letter
            CALL    CON_OUT             ; print the character
            RET
.PD_DIGIT:
            ADD     A,'0'               ; convert to digit
            CALL    CON_OUT             ; print the character
            RET

STR_CMP:      ; DE = string1, HL = string2, returns Z if equal
            PUSH    DE
            PUSH    HL
.SC_LOOP:
            LD      A,(DE)
            LD      B,A                  ; save char from string1
            LD      A,(HL)
            CP      B
            JR      NZ,.SC_DONE          ; if different then NZ and not equal
            OR      A
            JR      Z,.SC_DONE           ; both are zero => equal
            INC     DE
            INC     HL
            JR      .SC_LOOP
.SC_DONE:
            POP     HL
            POP     DE
            RET

; -----------------------------
; GPIO string I/O
; -----------------------------
READ_STRING: ; read until CRLF and print readable chars
            CALL    GPIO_INPUT
READ_STRING_INP:                            ; sometimes we want to read the string without waiting for valid as may already be set by SLAPI;
            LD      DE,STR_RX
            CALL    PRINT_Z
            XOR     A
            LD      (GOTCR),A
.RS_LOOP:
            CALL    READ_BYTE
            LD      B,A
            CALL    PRINT_ESCAPED

            LD      A,(GOTCR)
            OR      A
            JR      Z,.RS_CHECK_CR
            LD      A,B
            CP      0Ah
            JR      Z,.RS_DONE
            XOR     A
            LD      (GOTCR),A
            JR      .RS_LOOP

.RS_CHECK_CR:
            LD      A,B
            CP      0Dh
            JR      NZ,.RS_LOOP
            LD      A,01h
            LD      (GOTCR),A
            JR      .RS_LOOP

.RS_DONE:
            RET

WAIT_FOR_CHAR: ; A = target char (used for EOT)
            LD      (WAITCHAR),A
            CALL    GPIO_INPUT
            LD      DE,STR_RX
            CALL    PRINT_Z
.WFC_LOOP:
            CALL    READ_BYTE
            LD      B,A
            LD      A,(WAITCHAR)
            CP      B
            RET     Z
            CALL    PRINT_ESCAPED
            JR      .WFC_LOOP

SEND_Z:     ; DE -> zero-terminated string
            CALL    GPIO_OUTPUT
            PUSH    DE
            LD      DE,STR_TX
            CALL    PRINT_Z
            POP     DE
            CALL    SEND_Z_OUT
            LD      A,100
            CALL    DELAY_MS            ; Hold lines for a moment so other end can read
            RET

SEND_Z_OUT:
.SZ_LOOP:
            LD      A,(DE)
            OR      A
            JR      Z,.SZ_END
            CALL    CON_OUT
            CALL    SEND_BYTE
            INC     DE
            JR      .SZ_LOOP
.SZ_END:
            RET


READ_BYTE:
            CALL    READ_NIBBLE
            SLA     A
            SLA     A
            SLA     A
            SLA     A
            LD      B,A
            CALL    READ_NIBBLE
            AND     0Fh
            OR      B
            ; CALL    PRINT_HEX
            RET

SEND_BYTE:
            LD      B,A
            SRL     A
            SRL     A
            SRL     A
            SRL     A
            CALL    SEND_NIBBLE
            LD      A,B
            AND     0Fh
            CALL    SEND_NIBBLE
            RET

READ_NIBBLE:
            CALL    CLEAR_ACK
            CALL    WAIT_VALID_SET
            CALL    READ_DATA
            CALL    SET_ACK
            LD      A,50
            CALL    DELAY_MS
            LD      A,(NB)
            RET

SEND_NIBBLE:
            LD      (NB),A
            CALL    CLEAR_VALID
            CALL    WAIT_ACK_CLEAR
            CALL    WRITE_DATA
            CALL    SET_VALID
            CALL    WAIT_ACK_SET
            RET

; -----------------------------
; GPIO low-level
; -----------------------------
WAIT_VALID_SET:
.WVS_LOOP:
            LD      A,GPIOAR
            OUT     (REGSELPORT),A
            IN      A,(REGDATAPORT)
            AND     VALIDBIT
            JR      Z,.WVS_LOOP
            RET

WAIT_VALID_CLEAR:
.WVC_LOOP:
            LD      A,GPIOAR
            OUT     (REGSELPORT),A
            IN      A,(REGDATAPORT)
            AND     VALIDBIT
            JR      NZ,.WVC_LOOP
            RET

WAIT_ACK_SET:
.WAS_LOOP:
            LD      A,GPIOAR
            OUT     (REGSELPORT),A
            IN      A,(REGDATAPORT)
            AND     ACKBIT
            JR      Z,.WAS_LOOP
            RET

WAIT_ACK_CLEAR:
.WAC_LOOP:
            LD      A,GPIOAR
            OUT     (REGSELPORT),A
            IN      A,(REGDATAPORT)
            AND     ACKBIT
            JR      NZ,.WAC_LOOP
            RET

SET_VALID:
            LD      A,(NB)
            OR      VALIDBIT
            LD      (NB),A
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            LD      A,(NB)
            OUT     (REGDATAPORT),A
            RET

CLEAR_VALID:
            LD      A,(NB)
            AND     0EFh
            LD      (NB),A
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            LD      A,(NB)
            OUT     (REGDATAPORT),A
            RET

SET_ACK:
            LD      A,(NB)
            OR      ACKBIT
            LD      (NB),A
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            LD      A,(NB)
            OUT     (REGDATAPORT),A
            RET

CLEAR_ACK:
            LD      A,(NB)
            AND     0DFh
            LD      (NB),A
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            LD      A,(NB)
            OUT     (REGDATAPORT),A
            RET

WRITE_DATA:
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            LD      A,(NB)
            OUT     (REGDATAPORT),A
            RET

READ_DATA:
            LD      A,GPIOAR
            OUT     (REGSELPORT),A
            IN      A,(REGDATAPORT)
            AND     0Fh
            LD      (NB),A
            RET

GPIO_INPUT:
            CALL    GPIO_SET_INPUT
            CALL    WAIT_VALID_CLEAR
            RET

GPIO_SET_INPUT:
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            LD      A,IODIRA
            OUT     (REGSELPORT),A
            LD      A,0DFh             ; 0-3 input, 4 input, 5 output
            OUT     (REGDATAPORT),A

            LD      A,GPPUA
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            RET

GPIO_OUTPUT:
            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            LD      A,IODIRA
            OUT     (REGSELPORT),A
            LD      A,020h             ; 0-3 and 4 output, 5 input
            OUT     (REGDATAPORT),A

            LD      A,GPPUA
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            LD      A,GPIOAW
            OUT     (REGSELPORT),A
            XOR     A
            OUT     (REGDATAPORT),A

            CALL    WAIT_ACK_CLEAR

            RET

; -----------------------------
; Delay
; -----------------------------
DELAY_MS:    ; A = milliseconds to delay (8MHz), preserves all used regs except A
            PUSH    BC
            PUSH    DE
            LD      E,A
.DM_MS_LOOP:
            LD      A,E
            OR      A
            JR      Z,.DM_DONE

            LD      D,5               ; ~0.9985 ms per loop at 8MHz
.DM_OUTER_LOOP:
            LD      B,121
.DM_INNER_LOOP:
            DJNZ    .DM_INNER_LOOP
            DEC     D
            JR      NZ,.DM_OUTER_LOOP

            DEC     E
            JR      .DM_MS_LOOP
.DM_DONE:
            POP     DE
            POP     BC
            RET

DELAY_SHORT:
            LD      A, 10
            CALL    DELAY_MS
            RET

; -----------------------------
; Data
; -----------------------------
OLD_STACK:  DW      0000h
STACK:      DS      256
STACK_END:  EQU     $-1
NB:         DB      00h
GOTCR:      DB      00h
BSFLAG:     DB      00h
WAITCHAR:   DB      00h

INBUF:      DB      MAXLEN
            DB      0
INBUF_DATA: DS      MAXLEN
            DB      0

STR_PROMPT: DB      '>',0
STR_RX:     DB      '<= ',0
STR_TX:     DB      '=> ',0
STR_CRLF:   DB      13,10,0

STR_INTRO:  DB      'SLAPI ChatGPT Demo',13,10,0

STR_DOMAIN: DB      'DOMAIN api.openai.com',13,10,0
STR_HTTPS:  DB      'HTTPS',13,10,0
STR_HDR_JSON:
            DB      'HEADERS Content-Type application/json',13,10,0
STR_HDRS_OFF:
            DB      'RESPONSE HDRS_OFF',13,10,0

            INCLUDE "chatgpt_auth.inc"

STR_JSONPATH_CHAT:
            DB      'RESPONSE JSONPATH $.output[1].content[0].text',13,10,0
STR_POST_START:
            DB      'POST /v1/responses HTTP/1.1',13,10,13,10
            DB      '{ "model": "gpt-5-nano", "input": "',0
STR_POST_END:
            DB      '" }',13,10,13,10,0

STR_QUIT:    DB     '/QUIT',0

            END