#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>


int
main ( int argc, char **argv )
{
  int fd, r;
  unsigned char* adr = NULL;
  struct stat st;
  size_t size, i;
  unsigned short int sum;

  if (argc < 2) {
    fprintf(stderr, "One argument needed: path to file to checksum\n");
    exit(-1);
  }
  
  fd = open(argv[1], O_RDONLY );
  if (fd <= 0) {
    fprintf(stderr, "Can't open file\n");
    exit(-2);
  }
  r = fstat(fd, &st);
  if (r < 0) {
    fprintf(stderr, "Can't stat file\n");
    exit(-3);
  }
  size = st.st_size;

  adr = mmap(NULL, size, PROT_READ, MAP_SHARED, fd, 0);
  if (adr ==  MAP_FAILED) {
    fprintf(stderr, "Can't mmap file\n");
    exit(-3);
  }

  sum = 0;
  for (i = 0 ; i < size-2 ; i++) {
    sum += adr[i];
  }

  printf("Checksum is 0x%04x\n", sum);

  return 0;
}
