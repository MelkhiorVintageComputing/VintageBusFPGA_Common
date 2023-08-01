%{
/*
 * Copyright (c) 2023 Romain Dolbeau <romain@dolbeau.org>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "parser.h"
#include "parser_par.h"
%}

DIGIT           [0-9]
HEXPREFIX       "0x"
HEXDIGIT        [0-9a-fA-F]
SPACE           [ \t]
FCHARNAME       [[:alpha:]]
CHARNAME        [[:alnum:]_]

%%

{HEXPREFIX}{HEXDIGIT}{HEXDIGIT}* { yylval.num = strtol(yytext, NULL, 16); return NUM; }

{DIGIT}{DIGIT}* { yylval.num = strtol(yytext, NULL, 10); return NUM; }

{FCHARNAME}{CHARNAME}* { yylval.string = strdup(yytext); return NAME; }

,                               { return yytext[0]; }

\n                               { return yytext[0]; }

{SPACE}+                         { }

%%
