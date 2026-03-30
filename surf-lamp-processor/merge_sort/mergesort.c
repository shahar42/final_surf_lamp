#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct 
{
    float value;
    int index;
} IndexedValue;

#define SORT_TYPE   IndexedValue
#define SORT_SUFFIX indexed
#define SORT_LE(a, b) ((a).value <= (b).value)
#define SORT_GT(a, b) ((a).value > (b).value)
#include "mergesort_template.h"

#define SORT_TYPE   int
#define SORT_SUFFIX int
#include "mergesort_template.h"

#define SORT_TYPE   float
#define SORT_SUFFIX float
#include "mergesort_template.h"

#ifndef MERGESORT_NO_MAIN
int main(void)
{
    int iarr[] = {4, 7, 9, 11, 1, 2, 3, 5, 6, 8, 10, 12};
    int in = sizeof(iarr) / sizeof(iarr[0]);

    printf("int before:   ");
    for (int i = 0; i < in; i++) printf("%d ", iarr[i]);
    printf("\n");

    merge_sort_array_int(iarr, in);

    printf("int after:    ");
    for (int i = 0; i < in; i++) printf("%d ", iarr[i]);
    printf("\n\n");

    float farr[] = {3.14f, 1.41f, 2.72f, 0.57f, 1.73f, 0.01f};
    int fn = sizeof(farr) / sizeof(farr[0]);

    printf("float before: ");
    for (int i = 0; i < fn; i++) printf("%.2f ", farr[i]);
    printf("\n");

    merge_sort_array_float(farr, fn);

    printf("float after:  ");
    for (int i = 0; i < fn; i++) printf("%.2f ", farr[i]);
    printf("\n");

    return 0;
}
#endif