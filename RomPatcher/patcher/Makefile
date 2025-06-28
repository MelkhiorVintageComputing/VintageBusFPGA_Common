PATCHERSRC=patcher.c
PATCHEROBJ=$(PATCHERSRC:.cpp=.o)
PATCHERDEP=$(PATCHERSRC:.cpp=.d)
GENLINKSRC=genlink.c
GENLINKOBJ=$(GENLINKSRC:.cpp=.o)
GENLINKDEP=$(GENLINKSRC:.cpp=.d)
OOBJ=parser_par.o parser_lex.o
LEX=flex
YACC=bison -d #--report-file=bison.log --report=all
CC=gcc
CFLAGS=-O2

all: patcher genlink sun3_checksum

%.o: %.c
	$(CC) $(CFLAGS) $< -c -o $@

patcher: $(PATCHEROBJ) $(OOBJ)
	$(CC) $(CFLAGS) $^ -o $@

genlink: $(GENLINKOBJ) $(OOBJ)
	$(CC) $(CFLAGS) $^ -o $@

sun3_checksum: sun3_checksum.c
	$(CC) $(CFLAGS) $< -o $@

parser_par.h: parser_par.o

parser_par.o: parser_par.y
	$(YACC) -o $(<:%.y=%.c) $<
	$(CC) $(CFLAGS) $(<:%.y=%.c) -c -o $@

parser_lex.o: parser_lex.l parser_par.h
	$(LEX) -o $(<:%.l=%.c) $< 
	$(CC) $(CFLAGS) $(<:%.l=%.c) -c -o $@

%.d: %.cpp
	$(CXX) -MM $< -o $@

clean:
	rm -f $(PATCHEROBJ) patcher

veryclean:
	rm -f $(PATCHEROBJ) patcher *~ parser_lex.c parser_par.c *.d

ultraclean:
	rm -f $(PATCHEROBJ) patcher *~ parser_lex.c parser_par.c *.d *.scala


## avoid builtin rule for .o
.SUFFIXES:
SUFFIXES :=
%.o:
