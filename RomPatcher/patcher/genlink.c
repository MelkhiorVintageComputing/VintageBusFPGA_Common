#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

#include "parser.h"
#include "parser_par.h"

extern FILE *yyin, *yyout;
extern int yydebug;


int main(int argc, char **argv) {
  char* descfile = NULL;
  FILE *myfile;
  int c;
  azone zones[32];
  int nz = 0, i;
  
  while ((c = getopt(argc, argv, "d:")) != -1) {
    switch(c) {
    default:
      fprintf(stderr, "oups : %c\n", c);
      exit(-1);
      break;

    case 'd':
      descfile = strndup(optarg, 512);
      break;
    }
  }

  if (descfile == NULL) {
    fprintf(stderr, "no desc\n");
    exit(-4);
  }

  {
    myfile = fopen(descfile, "r");
    if (!myfile) {
      fprintf(stderr, "no desc file\n");
      exit(-5);
    }
    yyin = myfile;
    yyparse(zones, &nz);
    
    fclose(myfile);

    fprintf(stderr, "Found %d entries\n", nz);
  }

  fprintf(stdout,
	  "OUTPUT_FORMAT(\"elf32-m68k\");\n"
	  "SECTIONS {\n"
	  "  .text : {\n");

  for (i = 0 ; i < nz; i++) {
    fprintf(stdout, "  . = 0x%06x;\n", zones[i].address);
    fprintf(stdout, "  *(.text.%s)\n", zones[i].name);
    if (zones[i].size > 0) {
      fprintf(stdout, "  . = 0x%06x;\n", zones[i].address + zones[i].size);
      fprintf(stdout, "  *(.text.return%s)\n", zones[i].name);
    }
    fprintf(stdout, "\n");	
  }

  fprintf(stdout, "  }\n}\n");

  return 0;
}
