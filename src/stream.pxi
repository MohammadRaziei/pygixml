from libc.stdint cimport uint32_t, uint64_t

cdef extern from *:
    """
    /* The source files can be found through the homepage: https://dev.yorhel.nl/yxml */

    #ifdef __cplusplus
    extern "C" {
    #endif

    #include <string.h>
    #include <stdint.h>
    #include <stddef.h>

    #if defined(_MSC_VER) && !defined(__cplusplus) && !defined(inline)
    #define inline __inline
    #endif

    /* Full API documentation for this library can be found in the "yxml.md" file
    * in the yxml git repository, or online at http://dev.yorhel.nl/yxml/man */

    typedef enum {
        YXML_EEOF        = -5, /* Unexpected EOF                             */
        YXML_EREF        = -4, /* Invalid character or entity reference (&whatever;) */
        YXML_ECLOSE      = -3, /* Close tag does not match open tag (<Tag> .. </OtherTag>) */
        YXML_ESTACK      = -2, /* Stack overflow (too deeply nested tags or too long element/attribute name) */
        YXML_ESYN        = -1, /* Syntax error (unexpected byte)             */
        YXML_OK          =  0, /* Character consumed, no new token present   */
        YXML_ELEMSTART   =  1, /* Start of an element:   '<Tag ..'           */
        YXML_CONTENT     =  2, /* Element content                            */
        YXML_ELEMEND     =  3, /* End of an element:     '.. />' or '</Tag>' */
        YXML_ATTRSTART   =  4, /* Attribute:             'Name=..'           */
        YXML_ATTRVAL     =  5, /* Attribute value                            */
        YXML_ATTREND     =  6, /* End of attribute       '.."'               */
        YXML_PISTART     =  7, /* Start of a processing instruction          */
        YXML_PICONTENT   =  8, /* Content of a PI                            */
        YXML_PIEND       =  9  /* End of a processing instruction            */
    } yxml_ret_t;

    /* When, exactly, are tokens returned?
    *
    * <TagName
    *   '>' ELEMSTART
    *   '/' ELEMSTART, '>' ELEMEND
    *   ' ' ELEMSTART
    *     '>'
    *     '/', '>' ELEMEND
    *     Attr
    *       '=' ATTRSTART
    *         "X ATTRVAL
    *           'Y'  ATTRVAL
    *             'Z'  ATTRVAL
    *               '"' ATTREND
    *                 '>'
    *                 '/', '>' ELEMEND
    *
    * </TagName
    *   '>' ELEMEND
    */


    typedef struct {
        /* PUBLIC (read-only) */

        /* Name of the current element, zero-length if not in any element. Changed
        * after YXML_ELEMSTART. The pointer will remain valid up to and including
        * the next non-YXML_ATTR* token, the pointed-to buffer will remain valid
        * up to and including the YXML_ELEMEND for the corresponding element. */
        char *elem;

        /* The last read character(s) of an attribute value (YXML_ATTRVAL), element
        * data (YXML_CONTENT), or processing instruction (YXML_PICONTENT). Changed
        * after one of the respective YXML_ values is returned, and only valid
        * until the next yxml_parse() call. Usually, this string only consists of
        * a single byte, but multiple bytes are returned in the following cases:
        * - "<?SomePI ?x ?>": The two characters "?x"
        * - "<![CDATA[ ]x ]]>": The two characters "]x"
        * - "<![CDATA[ ]]x ]]>": The three characters "]]x"
        * - "&#N;" and "&#xN;", where dec(n) > 127. The referenced Unicode
        *   character is then encoded in multiple UTF-8 bytes.
        */
        char data[8];

        /* Name of the current attribute. Changed after YXML_ATTRSTART, valid up to
        * and including the next YXML_ATTREND. */
        char *attr;

        /* Name/target of the current processing instruction, zero-length if not in
        * a PI. Changed after YXML_PISTART, valid up to (but excluding)
        * the next YXML_PIEND. */
        char *pi;

        /* Line number, byte offset within that line, and total bytes read. These
        * values refer to the position _after_ the last byte given to
        * yxml_parse(). These are useful for debugging and error reporting. */
        uint64_t byte;
        uint64_t total;
        uint32_t line;


        /* PRIVATE */
        int state;
        unsigned char *stack; /* Stack of element names + attribute/PI name, separated by \0. Also starts with a \0. */
        size_t stacksize, stacklen;
        unsigned reflen;
        unsigned quote;
        int nextstate; /* Used for '@' state remembering and for the "string" consuming state */
        unsigned ignore;
        unsigned char *string;
    } yxml_t;


    #ifdef __cplusplus
    extern "C" {
    #endif

    void yxml_init(yxml_t *, void *, size_t);


    yxml_ret_t yxml_parse(yxml_t *, int);


    /* May be called after the last character has been given to yxml_parse().
    * Returns YXML_OK if the XML document is valid, YXML_EEOF otherwise.  Using
    * this function isn't really necessary, but can be used to detect documents
    * that don't end correctly. In particular, an error is returned when the XML
    * document did not contain a (complete) root element, or when the document
    * ended while in a comment or processing instruction. */
    yxml_ret_t yxml_eof(yxml_t *);

    #ifdef __cplusplus
    }
    #endif


    /* Returns the length of the element name (x->elem), attribute name (x->attr),
    * or PI name (x->pi). This function should ONLY be used directly after the
    * YXML_ELEMSTART, YXML_ATTRSTART or YXML_PISTART (respectively) tokens have
    * been returned by yxml_parse(), calling this at any other time may not give
    * the correct results. This function should also NOT be used on strings other
    * than x->elem, x->attr or x->pi. */
    static inline size_t yxml_symlen(yxml_t *x, const char *s) {
        return (x->stack + x->stacklen) - (const unsigned char*)s;
    }

    typedef enum {
        YXMLS_string,
        YXMLS_attr0,
        YXMLS_attr1,
        YXMLS_attr2,
        YXMLS_attr3,
        YXMLS_attr4,
        YXMLS_cd0,
        YXMLS_cd1,
        YXMLS_cd2,
        YXMLS_comment0,
        YXMLS_comment1,
        YXMLS_comment2,
        YXMLS_comment3,
        YXMLS_comment4,
        YXMLS_dt0,
        YXMLS_dt1,
        YXMLS_dt2,
        YXMLS_dt3,
        YXMLS_dt4,
        YXMLS_elem0,
        YXMLS_elem1,
        YXMLS_elem2,
        YXMLS_elem3,
        YXMLS_enc0,
        YXMLS_enc1,
        YXMLS_enc2,
        YXMLS_enc3,
        YXMLS_etag0,
        YXMLS_etag1,
        YXMLS_etag2,
        YXMLS_init,
        YXMLS_le0,
        YXMLS_le1,
        YXMLS_le2,
        YXMLS_le3,
        YXMLS_lee1,
        YXMLS_lee2,
        YXMLS_leq0,
        YXMLS_misc0,
        YXMLS_misc1,
        YXMLS_misc2,
        YXMLS_misc2a,
        YXMLS_misc3,
        YXMLS_pi0,
        YXMLS_pi1,
        YXMLS_pi2,
        YXMLS_pi3,
        YXMLS_pi4,
        YXMLS_std0,
        YXMLS_std1,
        YXMLS_std2,
        YXMLS_std3,
        YXMLS_ver0,
        YXMLS_ver1,
        YXMLS_ver2,
        YXMLS_ver3,
        YXMLS_xmldecl0,
        YXMLS_xmldecl1,
        YXMLS_xmldecl2,
        YXMLS_xmldecl3,
        YXMLS_xmldecl4,
        YXMLS_xmldecl5,
        YXMLS_xmldecl6,
        YXMLS_xmldecl7,
        YXMLS_xmldecl8,
        YXMLS_xmldecl9
    } yxml_state_t;


    #define yxml_isChar(c) 1
    /* 0xd should be part of SP, too, but yxml_parse() already normalizes that into 0xa */
    #define yxml_isSP(c) (c == 0x20 || c == 0x09 || c == 0x0a)
    #define yxml_isAlpha(c) ((c|32)-'a' < 26)
    #define yxml_isNum(c) (c-'0' < 10)
    #define yxml_isHex(c) (yxml_isNum(c) || (c|32)-'a' < 6)
    #define yxml_isEncName(c) (yxml_isAlpha(c) || yxml_isNum(c) || c == '.' || c == '_' || c == '-')
    #define yxml_isNameStart(c) (yxml_isAlpha(c) || c == ':' || c == '_' || c >= 128)
    #define yxml_isName(c) (yxml_isNameStart(c) || yxml_isNum(c) || c == '-' || c == '.')
    /* XXX: The valid characters are dependent on the quote char, hence the access to x->quote */
    #define yxml_isAttValue(c) (yxml_isChar(c) && c != x->quote && c != '<' && c != '&')
    /* Anything between '&' and ';', the yxml_ref* functions will do further
    * validation. Strictly speaking, this is "yxml_isName(c) || c == '#'", but
    * this parser doesn't understand entities with '.', ':', etc, anwyay.  */
    #define yxml_isRef(c) (yxml_isNum(c) || yxml_isAlpha(c) || c == '#')

    #define INTFROM5CHARS(a, b, c, d, e) ((((uint64_t)(a))<<32) | (((uint64_t)(b))<<24) | (((uint64_t)(c))<<16) | (((uint64_t)(d))<<8) | (uint64_t)(e))


    /* Set the given char value to ch (0<=ch<=255). */
    static inline void yxml_setchar(char *dest, unsigned ch) {
        *(unsigned char *)dest = ch;
    }


    /* Similar to yxml_setchar(), but will convert ch (any valid unicode point) to
    * UTF-8 and appends a '\\0'. dest must have room for at least 5 bytes. */
    static void yxml_setutf8(char *dest, unsigned ch) {
        if(ch <= 0x007F)
            yxml_setchar(dest++, ch);
        else if(ch <= 0x07FF) {
            yxml_setchar(dest++, 0xC0 | (ch>>6));
            yxml_setchar(dest++, 0x80 | (ch & 0x3F));
        } else if(ch <= 0xFFFF) {
            yxml_setchar(dest++, 0xE0 | (ch>>12));
            yxml_setchar(dest++, 0x80 | ((ch>>6) & 0x3F));
            yxml_setchar(dest++, 0x80 | (ch & 0x3F));
        } else {
            yxml_setchar(dest++, 0xF0 | (ch>>18));
            yxml_setchar(dest++, 0x80 | ((ch>>12) & 0x3F));
            yxml_setchar(dest++, 0x80 | ((ch>>6) & 0x3F));
            yxml_setchar(dest++, 0x80 | (ch & 0x3F));
        }
        *dest = 0;
    }


    static inline yxml_ret_t yxml_datacontent(yxml_t *x, unsigned ch) {
        yxml_setchar(x->data, ch);
        x->data[1] = 0;
        return YXML_CONTENT;
    }


    static inline yxml_ret_t yxml_datapi1(yxml_t *x, unsigned ch) {
        yxml_setchar(x->data, ch);
        x->data[1] = 0;
        return YXML_PICONTENT;
    }


    static inline yxml_ret_t yxml_datapi2(yxml_t *x, unsigned ch) {
        x->data[0] = '?';
        yxml_setchar(x->data+1, ch);
        x->data[2] = 0;
        return YXML_PICONTENT;
    }


    static inline yxml_ret_t yxml_datacd1(yxml_t *x, unsigned ch) {
        x->data[0] = ']';
        yxml_setchar(x->data+1, ch);
        x->data[2] = 0;
        return YXML_CONTENT;
    }


    static inline yxml_ret_t yxml_datacd2(yxml_t *x, unsigned ch) {
        x->data[0] = ']';
        x->data[1] = ']';
        yxml_setchar(x->data+2, ch);
        x->data[3] = 0;
        return YXML_CONTENT;
    }


    static inline yxml_ret_t yxml_dataattr(yxml_t *x, unsigned ch) {
        /* Normalize attribute values according to the XML spec section 3.3.3. */
        yxml_setchar(x->data, ch == 0x9 || ch == 0xa ? 0x20 : ch);
        x->data[1] = 0;
        return YXML_ATTRVAL;
    }


    static yxml_ret_t yxml_pushstack(yxml_t *x, char **res, unsigned ch) {
        if(x->stacklen+2 >= x->stacksize)
            return YXML_ESTACK;
        x->stacklen++;
        *res = (char *)x->stack+x->stacklen;
        x->stack[x->stacklen] = ch;
        x->stacklen++;
        x->stack[x->stacklen] = 0;
        return YXML_OK;
    }


    static yxml_ret_t yxml_pushstackc(yxml_t *x, unsigned ch) {
        if(x->stacklen+1 >= x->stacksize)
            return YXML_ESTACK;
        x->stack[x->stacklen] = ch;
        x->stacklen++;
        x->stack[x->stacklen] = 0;
        return YXML_OK;
    }


    static void yxml_popstack(yxml_t *x) {
        do
            x->stacklen--;
        while(x->stack[x->stacklen]);
    }


    static inline yxml_ret_t yxml_elemstart  (yxml_t *x, unsigned ch) { return yxml_pushstack(x, &x->elem, ch); }
    static inline yxml_ret_t yxml_elemname   (yxml_t *x, unsigned ch) { return yxml_pushstackc(x, ch); }
    static inline yxml_ret_t yxml_elemnameend(yxml_t *x, unsigned ch) { return YXML_ELEMSTART; }


    /* Also used in yxml_elemcloseend(), since this function just removes the last
    * element from the stack and returns ELEMEND. */
    static yxml_ret_t yxml_selfclose(yxml_t *x, unsigned ch) {
        yxml_popstack(x);
        if(x->stacklen) {
            x->elem = (char *)x->stack+x->stacklen-1;
            while(*(x->elem-1))
                x->elem--;
            return YXML_ELEMEND;
        }
        x->elem = (char *)x->stack;
        x->state = YXMLS_misc3;
        return YXML_ELEMEND;
    }


    static inline yxml_ret_t yxml_elemclose(yxml_t *x, unsigned ch) {
        if(*((unsigned char *)x->elem) != ch)
            return YXML_ECLOSE;
        x->elem++;
        return YXML_OK;
    }


    static inline yxml_ret_t yxml_elemcloseend(yxml_t *x, unsigned ch) {
        if(*x->elem)
            return YXML_ECLOSE;
        return yxml_selfclose(x, ch);
    }


    static inline yxml_ret_t yxml_attrstart  (yxml_t *x, unsigned ch) { return yxml_pushstack(x, &x->attr, ch); }
    static inline yxml_ret_t yxml_attrname   (yxml_t *x, unsigned ch) { return yxml_pushstackc(x, ch); }
    static inline yxml_ret_t yxml_attrnameend(yxml_t *x, unsigned ch) { return YXML_ATTRSTART; }
    static inline yxml_ret_t yxml_attrvalend (yxml_t *x, unsigned ch) { yxml_popstack(x); return YXML_ATTREND; }


    static inline yxml_ret_t yxml_pistart  (yxml_t *x, unsigned ch) { return yxml_pushstack(x, &x->pi, ch); }
    static inline yxml_ret_t yxml_piname   (yxml_t *x, unsigned ch) { return yxml_pushstackc(x, ch); }
    static inline yxml_ret_t yxml_piabort  (yxml_t *x, unsigned ch) { yxml_popstack(x); return YXML_OK; }
    static inline yxml_ret_t yxml_pinameend(yxml_t *x, unsigned ch) {
        return (x->pi[0]|32) == 'x' && (x->pi[1]|32) == 'm' && (x->pi[2]|32) == 'l' && !x->pi[3] ? YXML_ESYN : YXML_PISTART;
    }
    static inline yxml_ret_t yxml_pivalend (yxml_t *x, unsigned ch) { yxml_popstack(x); x->pi = (char *)x->stack; return YXML_PIEND; }


    static inline yxml_ret_t yxml_refstart(yxml_t *x, unsigned ch) {
        memset(x->data, 0, sizeof(x->data));
        x->reflen = 0;
        return YXML_OK;
    }


    static yxml_ret_t yxml_ref(yxml_t *x, unsigned ch) {
        if(x->reflen >= sizeof(x->data)-1)
            return YXML_EREF;
        yxml_setchar(x->data+x->reflen, ch);
        x->reflen++;
        return YXML_OK;
    }


    static yxml_ret_t yxml_refend(yxml_t *x, yxml_ret_t ret) {
        unsigned char *r = (unsigned char *)x->data;
        unsigned ch = 0;
        if(*r == '#') {
            if(r[1] == 'x')
                for(r += 2; yxml_isHex((unsigned)*r); r++)
                    ch = (ch<<4) + (*r <= '9' ? *r-'0' : (*r|32)-'a' + 10);
            else
                for(r++; yxml_isNum((unsigned)*r); r++)
                    ch = (ch*10) + (*r-'0');
            if(*r)
                ch = 0;
        } else {
            uint64_t i = INTFROM5CHARS(r[0], r[1], r[2], r[3], r[4]);
            ch =
                i == INTFROM5CHARS('l','t', 0,  0, 0) ? '<' :
                i == INTFROM5CHARS('g','t', 0,  0, 0) ? '>' :
                i == INTFROM5CHARS('a','m','p', 0, 0) ? '&' :
                i == INTFROM5CHARS('a','p','o','s',0) ? '\\'':
                i == INTFROM5CHARS('q','u','o','t',0) ? '"' : 0;
        }

        /* Codepoints not allowed in the XML 1.1 definition of a Char */
        if(!ch || ch > 0x10FFFF || ch == 0xFFFE || ch == 0xFFFF || (ch-0xDFFF) < 0x7FF)
            return YXML_EREF;
        yxml_setutf8(x->data, ch);
        return ret;
    }


    static inline yxml_ret_t yxml_refcontent(yxml_t *x, unsigned ch) { return yxml_refend(x, YXML_CONTENT); }
    static inline yxml_ret_t yxml_refattrval(yxml_t *x, unsigned ch) { return yxml_refend(x, YXML_ATTRVAL); }


    void yxml_init(yxml_t *x, void *stack, size_t stacksize) {
        memset(x, 0, sizeof(*x));
        x->line = 1;
        x->stack = (unsigned char*)stack;
        x->stacksize = stacksize;
        *x->stack = 0;
        x->elem = x->pi = x->attr = (char *)x->stack;
        x->state = YXMLS_init;
    }


    yxml_ret_t yxml_parse(yxml_t *x, int _ch) {
        /* Ensure that characters are in the range of 0..255 rather than -126..125.
        * All character comparisons are done with positive integers. */
        unsigned ch = (unsigned)(_ch+256) & 0xff;
        if(!ch)
            return YXML_ESYN;
        x->total++;

        /* End-of-Line normalization, "\\rX", "\\r\\n" and "\\n" are recognized and
        * normalized to a single '\\n' as per XML 1.0 section 2.11. XML 1.1 adds
        * some non-ASCII character sequences to this list, but we can only handle
        * ASCII here without making assumptions about the input encoding. */
        if(x->ignore == ch) {
            x->ignore = 0;
            return YXML_OK;
        }
        x->ignore = (ch == 0xd) * 0xa;
        if(ch == 0xa || ch == 0xd) {
            ch = 0xa;
            x->line++;
            x->byte = 0;
        }
        x->byte++;

        switch((yxml_state_t)x->state) {
        case YXMLS_string:
            if(ch == *x->string) {
                x->string++;
                if(!*x->string)
                    x->state = x->nextstate;
                return YXML_OK;
            }
            break;
        case YXMLS_attr0:
            if(yxml_isName(ch))
                return yxml_attrname(x, ch);
            if(yxml_isSP(ch)) {
                x->state = YXMLS_attr1;
                return yxml_attrnameend(x, ch);
            }
            if(ch == (unsigned char)'=') {
                x->state = YXMLS_attr2;
                return yxml_attrnameend(x, ch);
            }
            break;
        case YXMLS_attr1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'=') {
                x->state = YXMLS_attr2;
                return YXML_OK;
            }
            break;
        case YXMLS_attr2:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_attr3;
                x->quote = ch;
                return YXML_OK;
            }
            break;
        case YXMLS_attr3:
            if(yxml_isAttValue(ch))
                return yxml_dataattr(x, ch);
            if(ch == (unsigned char)'&') {
                x->state = YXMLS_attr4;
                return yxml_refstart(x, ch);
            }
            if(x->quote == ch) {
                x->state = YXMLS_elem2;
                return yxml_attrvalend(x, ch);
            }
            break;
        case YXMLS_attr4:
            if(yxml_isRef(ch))
                return yxml_ref(x, ch);
            if(ch == (unsigned char)'\\x3b') {
                x->state = YXMLS_attr3;
                return yxml_refattrval(x, ch);
            }
            break;
        case YXMLS_cd0:
            if(ch == (unsigned char)']') {
                x->state = YXMLS_cd1;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return yxml_datacontent(x, ch);
            break;
        case YXMLS_cd1:
            if(ch == (unsigned char)']') {
                x->state = YXMLS_cd2;
                return YXML_OK;
            }
            if(yxml_isChar(ch)) {
                x->state = YXMLS_cd0;
                return yxml_datacd1(x, ch);
            }
            break;
        case YXMLS_cd2:
            if(ch == (unsigned char)']')
                return yxml_datacontent(x, ch);
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return YXML_OK;
            }
            if(yxml_isChar(ch)) {
                x->state = YXMLS_cd0;
                return yxml_datacd2(x, ch);
            }
            break;
        case YXMLS_comment0:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment1;
                return YXML_OK;
            }
            break;
        case YXMLS_comment1:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment2;
                return YXML_OK;
            }
            break;
        case YXMLS_comment2:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment3;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return YXML_OK;
            break;
        case YXMLS_comment3:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment4;
                return YXML_OK;
            }
            if(yxml_isChar(ch)) {
                x->state = YXMLS_comment2;
                return YXML_OK;
            }
            break;
        case YXMLS_comment4:
            if(ch == (unsigned char)'>') {
                x->state = x->nextstate;
                return YXML_OK;
            }
            break;
        case YXMLS_dt0:
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc1;
                return YXML_OK;
            }
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_dt1;
                x->quote = ch;
                x->nextstate = YXMLS_dt0;
                return YXML_OK;
            }
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_dt2;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return YXML_OK;
            break;
        case YXMLS_dt1:
            if(x->quote == ch) {
                x->state = x->nextstate;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return YXML_OK;
            break;
        case YXMLS_dt2:
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi0;
                x->nextstate = YXMLS_dt0;
                return YXML_OK;
            }
            if(ch == (unsigned char)'!') {
                x->state = YXMLS_dt3;
                return YXML_OK;
            }
            break;
        case YXMLS_dt3:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment1;
                x->nextstate = YXMLS_dt0;
                return YXML_OK;
            }
            if(yxml_isChar(ch)) {
                x->state = YXMLS_dt4;
                return YXML_OK;
            }
            break;
        case YXMLS_dt4:
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_dt1;
                x->quote = ch;
                x->nextstate = YXMLS_dt4;
                return YXML_OK;
            }
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_dt0;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return YXML_OK;
            break;
        case YXMLS_elem0:
            if(yxml_isName(ch))
                return yxml_elemname(x, ch);
            if(yxml_isSP(ch)) {
                x->state = YXMLS_elem1;
                return yxml_elemnameend(x, ch);
            }
            if(ch == (unsigned char)'/') {
                x->state = YXMLS_elem3;
                return yxml_elemnameend(x, ch);
            }
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return yxml_elemnameend(x, ch);
            }
            break;
        case YXMLS_elem1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'/') {
                x->state = YXMLS_elem3;
                return YXML_OK;
            }
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return YXML_OK;
            }
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_attr0;
                return yxml_attrstart(x, ch);
            }
            break;
        case YXMLS_elem2:
            if(yxml_isSP(ch)) {
                x->state = YXMLS_elem1;
                return YXML_OK;
            }
            if(ch == (unsigned char)'/') {
                x->state = YXMLS_elem3;
                return YXML_OK;
            }
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return YXML_OK;
            }
            break;
        case YXMLS_elem3:
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return yxml_selfclose(x, ch);
            }
            break;
        case YXMLS_enc0:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'=') {
                x->state = YXMLS_enc1;
                return YXML_OK;
            }
            break;
        case YXMLS_enc1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_enc2;
                x->quote = ch;
                return YXML_OK;
            }
            break;
        case YXMLS_enc2:
            if(yxml_isAlpha(ch)) {
                x->state = YXMLS_enc3;
                return YXML_OK;
            }
            break;
        case YXMLS_enc3:
            if(yxml_isEncName(ch))
                return YXML_OK;
            if(x->quote == ch) {
                x->state = YXMLS_xmldecl6;
                return YXML_OK;
            }
            break;
        case YXMLS_etag0:
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_etag1;
                return yxml_elemclose(x, ch);
            }
            break;
        case YXMLS_etag1:
            if(yxml_isName(ch))
                return yxml_elemclose(x, ch);
            if(yxml_isSP(ch)) {
                x->state = YXMLS_etag2;
                return yxml_elemcloseend(x, ch);
            }
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return yxml_elemcloseend(x, ch);
            }
            break;
        case YXMLS_etag2:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc2;
                return YXML_OK;
            }
            break;
        case YXMLS_init:
            if(ch == (unsigned char)'\\xef') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_misc0;
                x->string = (unsigned char *)"\\xbb\\xbf";
                return YXML_OK;
            }
            if(yxml_isSP(ch)) {
                x->state = YXMLS_misc0;
                return YXML_OK;
            }
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_le0;
                return YXML_OK;
            }
            break;
        case YXMLS_le0:
            if(ch == (unsigned char)'!') {
                x->state = YXMLS_lee1;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_leq0;
                return YXML_OK;
            }
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_elem0;
                return yxml_elemstart(x, ch);
            }
            break;
        case YXMLS_le1:
            if(ch == (unsigned char)'!') {
                x->state = YXMLS_lee1;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi0;
                x->nextstate = YXMLS_misc1;
                return YXML_OK;
            }
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_elem0;
                return yxml_elemstart(x, ch);
            }
            break;
        case YXMLS_le2:
            if(ch == (unsigned char)'!') {
                x->state = YXMLS_lee2;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi0;
                x->nextstate = YXMLS_misc2;
                return YXML_OK;
            }
            if(ch == (unsigned char)'/') {
                x->state = YXMLS_etag0;
                return YXML_OK;
            }
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_elem0;
                return yxml_elemstart(x, ch);
            }
            break;
        case YXMLS_le3:
            if(ch == (unsigned char)'!') {
                x->state = YXMLS_comment0;
                x->nextstate = YXMLS_misc3;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi0;
                x->nextstate = YXMLS_misc3;
                return YXML_OK;
            }
            break;
        case YXMLS_lee1:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment1;
                x->nextstate = YXMLS_misc1;
                return YXML_OK;
            }
            if(ch == (unsigned char)'D') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_dt0;
                x->string = (unsigned char *)"OCTYPE";
                return YXML_OK;
            }
            break;
        case YXMLS_lee2:
            if(ch == (unsigned char)'-') {
                x->state = YXMLS_comment1;
                x->nextstate = YXMLS_misc2;
                return YXML_OK;
            }
            if(ch == (unsigned char)'[') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_cd0;
                x->string = (unsigned char *)"CDATA[";
                return YXML_OK;
            }
            break;
        case YXMLS_leq0:
            if(ch == (unsigned char)'x') {
                x->state = YXMLS_xmldecl0;
                x->nextstate = YXMLS_misc1;
                return yxml_pistart(x, ch);
            }
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_pi1;
                x->nextstate = YXMLS_misc1;
                return yxml_pistart(x, ch);
            }
            break;
        case YXMLS_misc0:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_le0;
                return YXML_OK;
            }
            break;
        case YXMLS_misc1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_le1;
                return YXML_OK;
            }
            break;
        case YXMLS_misc2:
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_le2;
                return YXML_OK;
            }
            if(ch == (unsigned char)'&') {
                x->state = YXMLS_misc2a;
                return yxml_refstart(x, ch);
            }
            if(yxml_isChar(ch))
                return yxml_datacontent(x, ch);
            break;
        case YXMLS_misc2a:
            if(yxml_isRef(ch))
                return yxml_ref(x, ch);
            if(ch == (unsigned char)'\\x3b') {
                x->state = YXMLS_misc2;
                return yxml_refcontent(x, ch);
            }
            break;
        case YXMLS_misc3:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'<') {
                x->state = YXMLS_le3;
                return YXML_OK;
            }
            break;
        case YXMLS_pi0:
            if(yxml_isNameStart(ch)) {
                x->state = YXMLS_pi1;
                return yxml_pistart(x, ch);
            }
            break;
        case YXMLS_pi1:
            if(yxml_isName(ch))
                return yxml_piname(x, ch);
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi4;
                return yxml_pinameend(x, ch);
            }
            if(yxml_isSP(ch)) {
                x->state = YXMLS_pi2;
                return yxml_pinameend(x, ch);
            }
            break;
        case YXMLS_pi2:
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi3;
                return YXML_OK;
            }
            if(yxml_isChar(ch))
                return yxml_datapi1(x, ch);
            break;
        case YXMLS_pi3:
            if(ch == (unsigned char)'>') {
                x->state = x->nextstate;
                return yxml_pivalend(x, ch);
            }
            if(yxml_isChar(ch)) {
                x->state = YXMLS_pi2;
                return yxml_datapi2(x, ch);
            }
            break;
        case YXMLS_pi4:
            if(ch == (unsigned char)'>') {
                x->state = x->nextstate;
                return yxml_pivalend(x, ch);
            }
            break;
        case YXMLS_std0:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'=') {
                x->state = YXMLS_std1;
                return YXML_OK;
            }
            break;
        case YXMLS_std1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_std2;
                x->quote = ch;
                return YXML_OK;
            }
            break;
        case YXMLS_std2:
            if(ch == (unsigned char)'y') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_std3;
                x->string = (unsigned char *)"es";
                return YXML_OK;
            }
            if(ch == (unsigned char)'n') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_std3;
                x->string = (unsigned char *)"o";
                return YXML_OK;
            }
            break;
        case YXMLS_std3:
            if(x->quote == ch) {
                x->state = YXMLS_xmldecl8;
                return YXML_OK;
            }
            break;
        case YXMLS_ver0:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'=') {
                x->state = YXMLS_ver1;
                return YXML_OK;
            }
            break;
        case YXMLS_ver1:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'\\'' || ch == (unsigned char)'"') {
                x->state = YXMLS_string;
                x->quote = ch;
                x->nextstate = YXMLS_ver2;
                x->string = (unsigned char *)"1.";
                return YXML_OK;
            }
            break;
        case YXMLS_ver2:
            if(yxml_isNum(ch)) {
                x->state = YXMLS_ver3;
                return YXML_OK;
            }
            break;
        case YXMLS_ver3:
            if(yxml_isNum(ch))
                return YXML_OK;
            if(x->quote == ch) {
                x->state = YXMLS_xmldecl4;
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl0:
            if(ch == (unsigned char)'m') {
                x->state = YXMLS_xmldecl1;
                return yxml_piname(x, ch);
            }
            if(yxml_isName(ch)) {
                x->state = YXMLS_pi1;
                return yxml_piname(x, ch);
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi4;
                return yxml_pinameend(x, ch);
            }
            if(yxml_isSP(ch)) {
                x->state = YXMLS_pi2;
                return yxml_pinameend(x, ch);
            }
            break;
        case YXMLS_xmldecl1:
            if(ch == (unsigned char)'l') {
                x->state = YXMLS_xmldecl2;
                return yxml_piname(x, ch);
            }
            if(yxml_isName(ch)) {
                x->state = YXMLS_pi1;
                return yxml_piname(x, ch);
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_pi4;
                return yxml_pinameend(x, ch);
            }
            if(yxml_isSP(ch)) {
                x->state = YXMLS_pi2;
                return yxml_pinameend(x, ch);
            }
            break;
        case YXMLS_xmldecl2:
            if(yxml_isSP(ch)) {
                x->state = YXMLS_xmldecl3;
                return yxml_piabort(x, ch);
            }
            if(yxml_isName(ch)) {
                x->state = YXMLS_pi1;
                return yxml_piname(x, ch);
            }
            break;
        case YXMLS_xmldecl3:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'v') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_ver0;
                x->string = (unsigned char *)"ersion";
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl4:
            if(yxml_isSP(ch)) {
                x->state = YXMLS_xmldecl5;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_xmldecl9;
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl5:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_xmldecl9;
                return YXML_OK;
            }
            if(ch == (unsigned char)'e') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_enc0;
                x->string = (unsigned char *)"ncoding";
                return YXML_OK;
            }
            if(ch == (unsigned char)'s') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_std0;
                x->string = (unsigned char *)"tandalone";
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl6:
            if(yxml_isSP(ch)) {
                x->state = YXMLS_xmldecl7;
                return YXML_OK;
            }
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_xmldecl9;
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl7:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_xmldecl9;
                return YXML_OK;
            }
            if(ch == (unsigned char)'s') {
                x->state = YXMLS_string;
                x->nextstate = YXMLS_std0;
                x->string = (unsigned char *)"tandalone";
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl8:
            if(yxml_isSP(ch))
                return YXML_OK;
            if(ch == (unsigned char)'?') {
                x->state = YXMLS_xmldecl9;
                return YXML_OK;
            }
            break;
        case YXMLS_xmldecl9:
            if(ch == (unsigned char)'>') {
                x->state = YXMLS_misc1;
                return YXML_OK;
            }
            break;
        }
        return YXML_ESYN;
    }


    yxml_ret_t yxml_eof(yxml_t *x) {
        if(x->state != YXMLS_misc3)
            return YXML_EEOF;
        return YXML_OK;
    }

    #ifdef __cplusplus
    }
    #endif
    """

    

    # ------------------------------------------------------------------
    # Cython-visible declarations for the embedded yxml API (above).
    # Only the fields/functions actually used by the wrapper below are
    # declared; the real (full) definitions come from the verbatim C
    # source embedded in this same translation unit.
    # ------------------------------------------------------------------
    ctypedef struct yxml_t:
        char *elem
        char data[8]
        char *attr
        char *pi
        uint64_t byte
        uint64_t total
        uint32_t line

    void yxml_init(yxml_t *x, void *stack, size_t stacksize)
    int yxml_parse(yxml_t *x, int ch)
    int yxml_eof(yxml_t *x)
    size_t yxml_symlen(yxml_t *x, const char *s)


# ==========================================================================
# pygixml.stream -- fast, generator-based streaming ("pull") XML parsing
# ==========================================================================
#
# This is built on top of the embedded yxml library above: a tiny,
# dependency-free, incremental tokenizer that is fed one byte at a time and
# emits element/attribute/text/processing-instruction events as they
# complete. Unlike the pugixml-backed DOM (XMLDocument/XMLNode) and the
# objectify module, this never loads the whole document into a pugixml
# tree -- it is meant for XML that is too large (or arrives incrementally,
# e.g. from a socket) to parse as a whole.
#
# The public API mirrors the well-known xml.etree.ElementTree / lxml.etree
# "iterparse + clear()" idiom so it feels familiar:
#
#     for event, elem in pygixml.iterparse("big.xml", events=("end",)):
#         if elem.tag == "record":
#             handle(elem)
#             elem.clear()          # drop the subtree once processed
#
# or, for the very common "give me every <record>" pattern::
#
#     for elem in pygixml.iterfind("big.xml", "record"):
#         handle(elem)
#
# Notes / current limitations:
#   * Namespace prefixes are *not* resolved -- "<ns:tag>" is reported as
#     the literal tag "ns:tag", and xmlns/xmlns:* show up as ordinary
#     attributes (matching yxml's own behaviour).
#   * Comments and DOCTYPE declarations are recognised (so they don't
#     cause errors) but produce no events.
#   * StreamElement.find/findall implement a small, fast subset of
#     ElementTree's path syntax: "tag", "a/b/c", "*" and ".//tag".
#     Attribute predicates ("tag[@id='x']") are not supported.

from libc.stdlib cimport malloc, free
from libc.string cimport strlen
from collections import deque
import io
import os


cdef enum:
    YXML_EEOF      = -5
    YXML_EREF      = -4
    YXML_ECLOSE    = -3
    YXML_ESTACK    = -2
    YXML_ESYN      = -1
    YXML_OK        = 0
    YXML_ELEMSTART = 1
    YXML_CONTENT   = 2
    YXML_ELEMEND   = 3
    YXML_ATTRSTART = 4
    YXML_ATTRVAL   = 5
    YXML_ATTREND   = 6
    YXML_PISTART   = 7
    YXML_PICONTENT = 8
    YXML_PIEND     = 9


cdef dict _YXML_ERRORS = {
    YXML_EEOF:   "unexpected end of input",
    YXML_EREF:   "invalid character or entity reference",
    YXML_ECLOSE: "closing tag does not match the currently open element",
    YXML_ESTACK: "parser stack exhausted (element/attribute names too long, "
                  "or the document is nested too deeply for this stack_size)",
    YXML_ESYN:   "syntax error",
}


cdef _raise_yxml_error(yxml_t *x, int ret):
    msg = _YXML_ERRORS.get(ret, f"XML parse error ({ret})")
    raise PygiXMLError(f"{msg} (line {x.line}, byte {x.total})")


# A small set of characters that need escaping in a JSON string. Anything
# not in this set (and not a control character) is copied through as-is.
# This mirrors jsonify.pxi's C++ json_escape() byte-for-byte, just operating
# on a Python str instead of a null-terminated C string -- used by
# StreamElement.to_json() so converting a streamed element straight to JSON
# text never needs the `json` module or an intermediate dict/list.
cdef str _json_escape_str(str s):
    cdef list out = ['"']
    cdef Py_ssize_t i, n = len(s)
    cdef Py_ssize_t start = 0
    cdef str c
    for i in range(n):
        c = s[i]
        if c == '"' or c == '\\':
            if i > start:
                out.append(s[start:i])
            out.append('\\' + c)
            start = i + 1
        elif c == '\n':
            if i > start:
                out.append(s[start:i])
            out.append('\\n')
            start = i + 1
        elif c == '\r':
            if i > start:
                out.append(s[start:i])
            out.append('\\r')
            start = i + 1
        elif c == '\t':
            if i > start:
                out.append(s[start:i])
            out.append('\\t')
            start = i + 1
        elif ord(c) < 0x20:
            if i > start:
                out.append(s[start:i])
            out.append(f"\\u{ord(c):04x}")
            start = i + 1
    if start < n:
        out.append(s[start:n])
    out.append('"')
    return "".join(out)


cdef class StreamElement:
    """A small, ElementTree-like XML element produced while streaming.

    ``StreamElement`` is a standalone, lightweight node -- it is *not*
    connected to a pugixml document. Each instance has a ``tag``,
    ``attrib`` dict, optional ``text``/``tail`` strings, and a list of
    child :class:`StreamElement` nodes (accessible via iteration,
    indexing, ``len()``, or :attr:`children`).

    Call :meth:`clear` once you're done with an element (and its
    subtree) to free the memory it holds -- the classic ``iterparse``
    idiom for keeping peak memory low on huge documents.
    """

    cdef public str tag
    cdef public dict attrib
    cdef public object text
    cdef public object tail
    cdef list _children

    def __cinit__(self, str tag, dict attrib=None):
        self.tag = tag
        self.attrib = attrib if attrib is not None else {}
        self.text = None
        self.tail = None
        self._children = []

    def __repr__(self):
        return f"<StreamElement {self.tag!r} ({len(self._children)} children) at 0x{id(self):x}>"

    def __len__(self):
        return len(self._children)

    def __bool__(self):
        return len(self._children) > 0

    def __iter__(self):
        return iter(self._children)

    def __getitem__(self, index):
        return self._children[index]

    @property
    def children(self):
        """The list of direct child :class:`StreamElement` nodes."""
        return self._children

    def get(self, str key, default=None):
        """Return ``attrib.get(key, default)``."""
        return self.attrib.get(key, default)

    def keys(self):
        """Return the attribute names (a view over :attr:`attrib`)."""
        return self.attrib.keys()

    def items(self):
        """Return the ``(name, value)`` attribute pairs."""
        return self.attrib.items()

    def iter(self, str tag=None):
        """Depth-first iterate this element and all its descendants,
        optionally restricted to a given ``tag`` (``"*"`` or ``None``
        matches everything)."""
        if tag is None or tag == "*" or self.tag == tag:
            yield self
        for child in self._children:
            yield from (<StreamElement>child).iter(tag)

    def findall(self, str path):
        """Find descendants matching ``path``.

        Supports ``"tag"`` / ``"a/b/c"`` (direct-child traversal),
        ``"*"`` (any child) and ``".//tag"`` (any descendant). Returns a
        list, possibly empty.
        """
        cdef list current
        cdef list nxt
        if path in (".", ""):
            return [self]
        if path.startswith(".//"):
            wanted = path[3:]
            return [el for el in self.iter()
                    if el is not self and (wanted == "*" or (<StreamElement>el).tag == wanted)]
        current = [self]
        for part in path.split("/"):
            nxt = []
            for el in current:
                for child in (<StreamElement>el)._children:
                    if part == "*" or (<StreamElement>child).tag == part:
                        nxt.append(child)
            current = nxt
        return current

    def find(self, str path):
        """Return the first descendant matching ``path``, or ``None``.
        See :meth:`findall` for the supported path syntax."""
        results = self.findall(path)
        return results[0] if results else None

    def findtext(self, str path, default=None):
        """Return ``.text`` of the first match of ``path``, or *default*."""
        elem = self.find(path)
        if elem is None:
            return default
        text = (<StreamElement>elem).text
        return text if text is not None else default

    def clear(self):
        """Drop this element's attributes, text, tail and children,
        freeing the memory they hold (the element itself, e.g. as an
        already-appended child of its parent, is left in place)."""
        self.attrib = {}
        self.text = None
        self.tail = None
        self._children = []

    def to_dict(self, str attr_prefix="@", str cdata_key="#text",
                object force_list=None):
        """Convert this element (and its subtree) to a plain ``dict``,
        using the same convention as :func:`pygixml.jsonify.dumps`:

        * Attributes become ``{attr_prefix + name: value}`` entries.
        * A child tag that appears more than once (or is listed in
          *force_list*, or *force_list* is ``True``) becomes a ``list``;
          otherwise its value is used directly (no list wrapping).
        * Text content is folded in as *cdata_key* when the element also
          has attributes or children; otherwise the element's value
          *is* its text (a plain string), matching the scalar shortcut
          used elsewhere in pygixml's JSON conversion.
        * An element with no attributes, no children, and no text
          becomes ``None``.

        This only ever builds ``dict``/``list``/``str`` — no JSON text
        is produced. See :meth:`to_json` for a direct-to-string version
        that skips building this dict entirely.
        """
        cdef bint force_all = (force_list is True)
        cdef object force_set = None
        if not force_all and force_list:
            force_set = set(force_list)
        return self._to_dict(attr_prefix, cdata_key, force_all, force_set)

    cdef object _to_dict(self, str attr_prefix, str cdata_key,
                          bint force_all, object force_set):
        cdef dict result
        cdef StreamElement child
        cdef str tag
        cdef list group
        cdef dict counts = {}
        cdef bint has_attrs = (len(self.attrib) > 0)
        cdef bint has_children = (len(self._children) > 0)
        cdef bint has_text = (self.text is not None and not self.text.isspace())

        if not has_attrs and not has_children:
            return self.text if has_text else None

        result = {}
        for k, v in self.attrib.items():
            result[attr_prefix + k] = v

        if has_text and (has_attrs or has_children):
            result[cdata_key] = self.text

        for child in self._children:
            tag = child.tag
            counts[tag] = counts.get(tag, 0) + 1

        cdef dict seen_as_list = {}
        for child in self._children:
            tag = child.tag
            value = child._to_dict(attr_prefix, cdata_key, force_all, force_set)
            as_list = (counts[tag] > 1) or force_all or \
                (force_set is not None and tag in force_set)
            if tag in seen_as_list:
                result[tag].append(value)
            elif as_list:
                result[tag] = [value]
                seen_as_list[tag] = True
            else:
                result[tag] = value

        return result

    def to_json(self, str attr_prefix="@", str cdata_key="#text",
                object force_list=None):
        """Serialize this element (and its subtree) directly to a JSON
        ``str`` — **without** ever constructing an intermediate ``dict``
        or ``list``, and without using the ``json`` module. Uses the
        same conventions as :meth:`to_dict`/:func:`jsonify.dumps`.

        This is the fast path for converting many elements one at a
        time (e.g. from :func:`pygixml.iterfind`) straight to JSON text,
        skipping the dict-building step entirely::

            for elem in pygixml.iterfind("big.xml", "record"):
                line = elem.to_json()   # str, ready to write/yield
                ...
                elem.clear()
        """
        cdef bint force_all = (force_list is True)
        cdef object force_set = None
        if not force_all and force_list:
            force_set = set(force_list)
        cdef list parts = []
        self._to_json(parts, attr_prefix, cdata_key, force_all, force_set)
        return "".join(parts)

    cdef void _to_json(self, list parts, str attr_prefix, str cdata_key,
                        bint force_all, object force_set):
        cdef StreamElement child
        cdef str tag
        cdef dict counts = {}
        cdef bint has_attrs = (len(self.attrib) > 0)
        cdef bint has_children = (len(self._children) > 0)
        cdef bint has_text = (self.text is not None and not self.text.isspace())
        cdef bint first
        cdef bint as_list
        cdef bint first_item

        if not has_attrs and not has_children:
            if has_text:
                parts.append(_json_escape_str(self.text))
            else:
                parts.append("null")
            return

        parts.append("{")
        first = True

        for k, v in self.attrib.items():
            if not first:
                parts.append(",")
            first = False
            parts.append(_json_escape_str(attr_prefix + k))
            parts.append(":")
            parts.append(_json_escape_str(v))

        if has_text and (has_attrs or has_children):
            if not first:
                parts.append(",")
            first = False
            parts.append(_json_escape_str(cdata_key))
            parts.append(":")
            parts.append(_json_escape_str(self.text))

        for child in self._children:
            tag = child.tag
            counts[tag] = counts.get(tag, 0) + 1

        cdef set emitted = set()
        for child in self._children:
            tag = child.tag
            if tag in emitted:
                continue
            emitted.add(tag)

            as_list = (counts[tag] > 1) or force_all or \
                (force_set is not None and tag in force_set)

            if not first:
                parts.append(",")
            first = False
            parts.append(_json_escape_str(tag))
            parts.append(":")

            if as_list:
                parts.append("[")
                first_item = True
                for sib in self._children:
                    if (<StreamElement>sib).tag != tag:
                        continue
                    if not first_item:
                        parts.append(",")
                    first_item = False
                    (<StreamElement>sib)._to_json(parts, attr_prefix, cdata_key,
                                                    force_all, force_set)
                parts.append("]")
            else:
                child._to_json(parts, attr_prefix, cdata_key, force_all, force_set)

        parts.append("}")


cdef class PullParser:
    """An incremental ("push") XML parser.

    Feed it bytes as they become available via :meth:`feed`, then drain
    completed ``("start" | "end" | "pi", value)`` events with
    :meth:`read_events`. Call :meth:`close` once there is no more input.

    This is the low-level engine behind :func:`iterparse`; use it
    directly when XML data arrives incrementally (e.g. from a socket or
    an async stream) rather than from a file you can simply read in
    chunks.

    :param events: subset of ``("start", "end", "pi")`` -- which events
        :meth:`read_events` produces. The element tree is always built
        regardless of *events*; this only controls what is yielded.
    :param tag: if given, only elements whose tag equals *tag* produce
        ``"start"``/``"end"`` events (their subtrees are still built and
        linked into the document as usual).
    :param stack_size: size in bytes of yxml's internal name stack. Must
        be large enough to hold the names of all simultaneously-open
        elements/attributes/PIs plus their nesting depth (each name is
        stored with a trailing NUL). Increase this for documents with
        very deep nesting or very long tag/attribute names.

    Example::

        parser = pygixml.PullParser(events=("start", "end"))
        for chunk in network_stream:
            parser.feed(chunk)
            for event, elem in parser.read_events():
                ...
        parser.close()
        for event, elem in parser.read_events():
            ...
    """

    cdef yxml_t _x
    cdef unsigned char *_stack_buf
    cdef object _queue
    cdef object _pending
    cdef list _elem_stack
    cdef bytearray _text_buf
    cdef bytearray _attrval_buf
    cdef bytearray _pi_buf
    cdef str _cur_attr
    cdef str _cur_pi
    cdef bint _closed
    cdef bint _want_start
    cdef bint _want_end
    cdef bint _want_pi
    cdef str _tag_filter

    def __cinit__(self, events=("end",), tag=None, size_t stack_size=4096):
        if stack_size < 64:
            raise ValueError("stack_size must be at least 64 bytes")

        self._stack_buf = <unsigned char*>malloc(stack_size)
        if self._stack_buf is NULL:
            raise MemoryError("could not allocate yxml parser stack")
        yxml_init(&self._x, <void*>self._stack_buf, stack_size)

        self._queue = deque()
        self._pending = None
        self._elem_stack = []
        self._text_buf = bytearray()
        self._attrval_buf = bytearray()
        self._pi_buf = bytearray()
        self._cur_attr = None
        self._cur_pi = None
        self._closed = False

        cdef tuple ev = tuple(events)
        for e in ev:
            if e not in ("start", "end", "pi"):
                raise ValueError(f"unknown event type: {e!r}")
        self._want_start = "start" in ev
        self._want_end = "end" in ev
        self._want_pi = "pi" in ev
        self._tag_filter = tag

    def __dealloc__(self):
        if self._stack_buf is not NULL:
            free(self._stack_buf)
            self._stack_buf = NULL

    @property
    def line(self):
        """Current 1-based line number -- useful in error messages."""
        return self._x.line

    @property
    def position(self):
        """Total number of bytes consumed so far."""
        return self._x.total

    @property
    def closed(self):
        return self._closed

    cdef inline void _flush_text(self):
        if not self._text_buf:
            return
        text = self._text_buf.decode("utf-8")
        self._text_buf = bytearray()
        if self._elem_stack:
            cur = <StreamElement>self._elem_stack[len(self._elem_stack) - 1]
            if cur._children:
                (<StreamElement>cur._children[len(cur._children) - 1]).tail = text
            else:
                cur.text = text

    cdef inline void _finalize_pending(self):
        cdef StreamElement elem
        if self._pending is not None:
            elem = <StreamElement>self._pending
            self._pending = None
            if self._elem_stack:
                (<StreamElement>self._elem_stack[len(self._elem_stack) - 1])._children.append(elem)
            if self._want_start and (self._tag_filter is None or elem.tag == self._tag_filter):
                self._queue.append(("start", elem))
            self._elem_stack.append(elem)

    def feed(self, bytes data):
        """Feed a chunk of well-formed, UTF-8 encoded XML bytes.

        Completed events become available through :meth:`read_events`.
        Raises :class:`PygiXMLError` on malformed XML.
        """
        if self._closed:
            raise PygiXMLError("PullParser is already closed")

        cdef Py_ssize_t i, n = len(data)
        cdef unsigned char c
        cdef int ret
        cdef Py_ssize_t symlen
        cdef bytes name
        cdef char *cdata
        cdef StreamElement elem

        for i in range(n):
            c = data[i]
            ret = yxml_parse(&self._x, c)

            if ret == YXML_OK:
                continue

            elif ret == YXML_ELEMSTART:
                self._finalize_pending()
                self._flush_text()
                symlen = <Py_ssize_t>yxml_symlen(&self._x, self._x.elem)
                name = self._x.elem[:symlen]
                self._pending = StreamElement(name.decode("utf-8"))

            elif ret == YXML_CONTENT:
                self._finalize_pending()
                cdata = self._x.data
                self._text_buf += cdata[:<Py_ssize_t>strlen(cdata)]

            elif ret == YXML_ELEMEND:
                self._finalize_pending()
                self._flush_text()
                elem = <StreamElement>self._elem_stack.pop()
                if self._want_end and (self._tag_filter is None or elem.tag == self._tag_filter):
                    self._queue.append(("end", elem))

            elif ret == YXML_ATTRSTART:
                symlen = <Py_ssize_t>yxml_symlen(&self._x, self._x.attr)
                name = self._x.attr[:symlen]
                self._cur_attr = name.decode("utf-8")
                self._attrval_buf = bytearray()

            elif ret == YXML_ATTRVAL:
                cdata = self._x.data
                self._attrval_buf += cdata[:<Py_ssize_t>strlen(cdata)]

            elif ret == YXML_ATTREND:
                (<StreamElement>self._pending).attrib[self._cur_attr] = \
                    self._attrval_buf.decode("utf-8")
                self._cur_attr = None

            elif ret == YXML_PISTART:
                self._finalize_pending()
                self._flush_text()
                symlen = <Py_ssize_t>yxml_symlen(&self._x, self._x.pi)
                name = self._x.pi[:symlen]
                self._cur_pi = name.decode("utf-8")
                self._pi_buf = bytearray()

            elif ret == YXML_PICONTENT:
                cdata = self._x.data
                self._pi_buf += cdata[:<Py_ssize_t>strlen(cdata)]

            elif ret == YXML_PIEND:
                if self._want_pi:
                    self._queue.append(("pi", (self._cur_pi, self._pi_buf.decode("utf-8"))))
                self._cur_pi = None

            else:
                _raise_yxml_error(&self._x, ret)

    def close(self):
        """Signal end-of-input.

        Validates that the document ended in a valid state (e.g. not
        mid-comment or with unclosed elements) and flushes any
        remaining buffered text. Safe to call multiple times.
        """
        if self._closed:
            return
        self._closed = True
        cdef int ret = yxml_eof(&self._x)
        if ret < 0:
            _raise_yxml_error(&self._x, ret)
        self._finalize_pending()
        self._flush_text()
        if self._elem_stack:
            raise PygiXMLError("unexpected end of input: unclosed element(s)")

    def read_events(self):
        """Iterate over ``(event, value)`` pairs accumulated so far.

        ``event`` is ``"start"``, ``"end"`` or ``"pi"``. For
        ``"start"``/``"end"``, *value* is a :class:`StreamElement`
        (the same instance for both events of a given element). For
        ``"pi"``, *value* is a ``(target, content)`` tuple.

        Draining this generator removes the events from the internal
        queue -- each event is only produced once.
        """
        while self._queue:
            yield self._queue.popleft()


def iterparse(source, events=("end",), tag=None,
               size_t stack_size=4096, Py_ssize_t chunk_size=65536):
    """Incrementally parse a (possibly huge) XML document.

    Yields ``(event, element)`` pairs as each element completes, where
    ``element`` is a :class:`StreamElement`. This never loads the whole
    document into a pugixml tree; only the :class:`PullParser`'s
    lightweight element objects are kept.

    :param source: a file path (``str``/``os.PathLike``), a binary
        file-like object (anything with ``.read(n)``), or raw XML
        ``bytes``/``bytearray``.
    :param events: subset of ``("start", "end", "pi")``. Default
        ``("end",)``, matching :mod:`xml.etree.ElementTree`.
    :param tag: if given, only elements with this tag produce events
        (their subtrees are still built normally).
    :param stack_size: see :class:`PullParser`.
    :param chunk_size: how many bytes to read from *source* at a time.

    Example -- process every ``<record>`` while keeping memory bounded::

        for event, elem in pygixml.iterparse("big.xml", events=("end",)):
            if elem.tag == "record":
                handle(elem)
                elem.clear()
    """
    cdef bint should_close = False
    cdef bint first_chunk = True
    cdef object fh
    cdef bytes chunk

    if isinstance(source, (bytes, bytearray)):
        fh = io.BytesIO(bytes(source))
        should_close = True
    elif hasattr(source, "read"):
        fh = source
    elif isinstance(source, (str, os.PathLike)):
        fh = open(source, "rb")
        should_close = True
    else:
        raise TypeError(
            f"unsupported source type: {type(source)!r} "
            "(expected a path, bytes/bytearray, or a file-like object with .read())"
        )

    parser = PullParser(events=events, tag=tag, stack_size=stack_size)
    try:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            if first_chunk:
                first_chunk = False
                if chunk[:3] == b"\xef\xbb\xbf":   # strip a leading UTF-8 BOM
                    chunk = chunk[3:]
            parser.feed(chunk)
            yield from parser.read_events()
        parser.close()
        yield from parser.read_events()
    finally:
        if should_close:
            fh.close()


def iterfind(source, str tag, size_t stack_size=4096, Py_ssize_t chunk_size=65536):
    """Shortcut for ``iterparse(source, events=("end",), tag=tag)`` that
    yields :class:`StreamElement` objects directly (no ``(event, elem)``
    tuples).

    Example::

        for record in pygixml.iterfind("big.xml", "record"):
            handle(record)
            record.clear()
    """
    for _event, elem in iterparse(source, events=("end",), tag=tag,
                                   stack_size=stack_size, chunk_size=chunk_size):
        yield elem


def iterjson(source, str tag, str attr_prefix="@", str cdata_key="#text",
             object force_list=None, size_t stack_size=4096,
             Py_ssize_t chunk_size=65536):
    """Stream-parse XML and yield each matching element as a **JSON
    string**, one at a time -- a generator, not a file.

    Built directly on :func:`iterfind` (the same tested, yxml-backed
    streaming parser used throughout this module) plus
    :meth:`StreamElement.to_json`, which serializes one element straight
    to a ``str`` without ever constructing an intermediate ``dict`` and
    without using the ``json`` module. Each yielded string is exactly
    what ``json.dumps()`` would produce for that element's
    :meth:`StreamElement.to_dict` -- but skips building the dict at all.

    Memory use is bounded by one element's subtree at a time (the same
    model as :func:`iterfind`/ElementTree's ``iterparse`` -- not the
    whole document), since each :class:`StreamElement` is discarded once
    its JSON string has been produced and the generator moves on.

    This is the right tool when you want JSON text *in Python* (to
    forward over a socket, push into a queue, write your own framing,
    etc.) without round-tripping through a file. If you actually want a
    ``.jsonl`` file on disk, see :func:`pygixml.jsonify.stream_dump_jsonl`
    instead -- that one streams from C++ all the way to the file, with
    no per-element Python object ever created.

    Parameters
    ----------
    source : str | os.PathLike | bytes | bytearray | file-like
        Same as :func:`iterparse`.
    tag : str
        Tag name of the elements to convert and yield.
    attr_prefix, cdata_key, force_list :
        Same meaning as :meth:`StreamElement.to_json`.
    stack_size, chunk_size :
        Same meaning as :func:`iterparse`.

    Example::

        for line in pygixml.iterjson("big.xml", "record"):
            send_to_queue(line)     # already a JSON string

        # writing a .jsonl file yourself, if you want one:
        with open("out.jsonl", "w") as f:
            for line in pygixml.iterjson("big.xml", "record"):
                f.write(line)
                f.write("\\n")
    """
    for elem in iterfind(source, tag, stack_size=stack_size, chunk_size=chunk_size):
        yield (<StreamElement>elem).to_json(attr_prefix, cdata_key, force_list)
        elem.clear()


def iterdict(source, str tag, str attr_prefix="@", str cdata_key="#text",
             object force_list=None, size_t stack_size=4096,
             Py_ssize_t chunk_size=65536):
    """Stream-parse XML and yield each matching element as a plain
    ``dict``, one at a time.

    Identical to :func:`iterjson` except it yields
    :meth:`StreamElement.to_dict` results instead of JSON strings --
    useful when you want to keep working with the data in Python rather
    than as text.

    Example::

        for record in pygixml.iterdict("big.xml", "record"):
            print(record["name"], record["@id"])
    """
    for elem in iterfind(source, tag, stack_size=stack_size, chunk_size=chunk_size):
        yield (<StreamElement>elem).to_dict(attr_prefix, cdata_key, force_list)
        elem.clear()
