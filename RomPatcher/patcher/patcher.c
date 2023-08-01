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
  char* patchedfile = NULL;
  char* inputfile = NULL;
  FILE *myfile;
  int c;
  azone zones[32];
  int nz = 0, i;
  unsigned long j;
  char *input;
  size_t input_size;
  char *patched;
  size_t patched_size;
  
  while ((c = getopt(argc, argv, "d:i:p:")) != -1) {
    switch(c) {
    default:
      fprintf(stderr, "oups : %c\n", c);
      exit(-1);
      break;

    case 'd':
      descfile = strndup(optarg, 512);
      break;

    case 'i':
      inputfile = strndup(optarg, 512);
      break;

    case 'p':
      patchedfile = strndup(optarg, 512);
      break;
    }
  }

  if (descfile == NULL) {
    fprintf(stderr, "no desc\n");
    exit(-4);
  }
  if (inputfile == NULL) {
    fprintf(stderr, "no input\n");
    exit(-2);
  }
  if (patchedfile == NULL) {
    fprintf(stderr, "nothing to patch\n");
    exit(-3);
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

    fprintf(stdout, "Found %d entries\n", nz);
  }

  {
    int fd;
    fd = open(inputfile, O_RDONLY | O_EXCL);
    if (fd == -1) {
      fprintf(stderr, "no input file\n");
      exit(-6);
    }
    struct stat statbuf;
    int err = fstat(fd, &statbuf);
    if (err < 0){
      fprintf(stderr, "no input file stat\n");
      close(fd);
      exit(-7);      
    }
    input_size = statbuf.st_size;
    input = mmap(NULL, input_size, PROT_READ, MAP_SHARED, fd, 0);
    if (input == MAP_FAILED){
      fprintf(stderr, "no input file map (%p for %s %zd: %d / %s)\n", input, inputfile, input_size, errno, strerror(errno));
      close(fd);
      exit(-8);
    }
    close(fd);
  }
  {
    int fd;
    fd = open(patchedfile, O_RDWR | O_EXCL);
    if (fd == -1) {
      fprintf(stderr, "no patched file\n");
      exit(-6);
    }
    struct stat statbuf;
    int err = fstat(fd, &statbuf);
    if (err < 0){
      fprintf(stderr, "no patched file stat\n");
      close(fd);
      exit(-7);      
    }
    
    patched_size = statbuf.st_size;
    patched = mmap(NULL, patched_size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    if (patched == MAP_FAILED){
      fprintf(stderr, "no patched file map\n");
      close(fd);
      exit(-8);
    }
    close(fd);
  }

  for (i = 0 ; i < nz; i++) {
    if (zones[i].size > 0) {
      fprintf(stdout, "Patching     [%08p:%08p[ (%s)\n", (void*)zones[i].address, (void*)(zones[i].address + zones[i].size), zones[i].name);
      for (j = zones[i].address; j < zones[i].address + zones[i].size; j++) {
	patched[j] = input[j];
      }
    } else {
      fprintf(stdout, "Not patching [%08p[ (%s)\n", (void*)zones[i].address, zones[i].name);
    }
  }

  munmap(input, input_size);
  munmap(patched, patched_size);

  return 0;
}
