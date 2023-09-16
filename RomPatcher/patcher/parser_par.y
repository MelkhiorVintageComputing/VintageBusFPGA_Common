%{
/*
 * Copyright (c) 2023 Romain Dolbeau <romain@dolbeau.org>
 * MIT License
 * See the LICENSE file at the top level of this software distribution for details.
 */
#include <stdio.h>
#include <stdlib.h>
#define YYDEBUG 1
#include "parser.h"
%}

%parse-param {azone *zones} {int *nz}

%union
{
  unsigned long num;
  char* string;
}

%token <num> NUM
%token <num> NAME

%%
input:      /* empty */ {  }
|  zone input        {  }
;

zone:
NUM ',' NUM ',' NAME { /* printf("0x%08lx %ld\n", $1, $3); */ zones[*nz].address = $1; zones[*nz].size = $3; zones[*nz].name = $5; (*nz)++;  }
| '\n'
;
%%

int
yyerror(char *s)
{
  fprintf(stderr, "error: %s\n", s);
  return(0);
}

int
yywrap(void)
{
  return(-1);
}
