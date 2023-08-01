#ifndef __PATCHER_H__
#define __PATCHER_H__

typedef struct {
  unsigned long address;
  unsigned long size;
  char* name;
} azone;

#endif // __PATCHER_H__
