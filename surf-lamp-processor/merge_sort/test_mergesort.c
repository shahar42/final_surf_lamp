#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <time.h>

extern void merge_sort_int(int arr[], int lo, int hi);
extern void merge_sort_array_int(int arr[], int n);
extern void merge_sort_float(float arr[], int lo, int hi);
extern void merge_sort_array_float(float arr[], int n);

static int total_pass = 0;
static int total_fail = 0;

static int cmp_int(const void *a, const void *b)
{
    int x = *(const int *)a, y = *(const int *)b;
    return (x > y) - (x < y);
}

static void check_int(const char *name, int *arr, int n)
{
    int *expected = malloc(n * sizeof(int));
    memcpy(expected, arr, n * sizeof(int));
    qsort(expected, n, sizeof(int), cmp_int);

    merge_sort_array_int(arr, n);

    if (memcmp(arr, expected, n * sizeof(int)) != 0) {
        printf("FAIL [int]: %s (n=%d)\n", name, n);
        if (n <= 40) {
            printf("  Got:      ");
            for (int i = 0; i < n; i++) printf("%d ", arr[i]);
            printf("\n  Expected: ");
            for (int i = 0; i < n; i++) printf("%d ", expected[i]);
            printf("\n");
        }
        total_fail++;
    } else {
        total_pass++;
    }
    free(expected);
}

static void test_int_edge_cases(void)
{
    merge_sort_array_int(NULL, 0);
    total_pass++;

    int a1[] = {42};
    check_int("single", a1, 1);

    int a2[] = {2, 1};
    check_int("two reversed", a2, 2);

    int a3[] = {1, 2};
    check_int("two sorted", a3, 2);

    int a4[] = {5, 5};
    check_int("two equal", a4, 2);
}

static void test_int_patterns(void)
{
    int a[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    check_int("already sorted", a, 10);

    int b[] = {10, 9, 8, 7, 6, 5, 4, 3, 2, 1};
    check_int("reverse", b, 10);

    int c[50];
    for (int i = 0; i < 50; i++) c[i] = 7;
    check_int("all equal", c, 50);

    int d[] = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5};
    check_int("duplicates", d, 11);

    int e[] = {-5, 3, -1, 0, -10, 7, 2, -3};
    check_int("negatives", e, 8);

    int f[] = {INT_MAX, INT_MIN, 0, INT_MAX, INT_MIN, 1, -1};
    check_int("INT extremes", f, 7);
}

static void test_int_sizes(void)
{
    for (int n = 2; n <= 64; n++) {
        int *a = malloc(n * sizeof(int));
        for (int i = 0; i < n; i++) a[i] = n - i;
        char name[32];
        snprintf(name, sizeof(name), "size %d", n);
        check_int(name, a, n);
        free(a);
    }
}

static void test_int_random(void)
{
    int sizes[] = {100, 255, 256, 257, 500, 1000, 1024, 4096, 10000, 50000, 100000};
    for (int s = 0; s < (int)(sizeof(sizes) / sizeof(sizes[0])); s++) {
        int n = sizes[s];
        int *a = malloc(n * sizeof(int));
        for (int i = 0; i < n; i++) a[i] = rand() % (n * 2) - n;
        char name[64];
        snprintf(name, sizeof(name), "random n=%d", n);
        check_int(name, a, n);
        free(a);
    }
}

static void test_int_preservation(void)
{
    int n = 1000;
    int *a = malloc(n * sizeof(int));
    int *b = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) a[i] = rand() % 20;
    memcpy(b, a, n * sizeof(int));
    qsort(b, n, sizeof(int), cmp_int);
    merge_sort_array_int(a, n);
    if (memcmp(a, b, n * sizeof(int)) == 0) {
        total_pass++;
    } else {
        printf("FAIL [int]: element preservation\n");
        total_fail++;
    }
    free(a);
    free(b);
}

static void test_int_large(void)
{
    int n = 1000000;
    int *a = malloc(n * sizeof(int));
    for (int i = 0; i < n; i++) a[i] = rand();
    clock_t t0 = clock();
    merge_sort_array_int(a, n);
    double ms = (double)(clock() - t0) / CLOCKS_PER_SEC * 1000.0;

    int ok = 1;
    for (int i = 1; i < n; i++)
        if (a[i] < a[i - 1]) { ok = 0; break; }

    if (ok) {
        printf("  int   large (1M): %.1f ms - PASS\n", ms);
        total_pass++;
    } else {
        printf("FAIL [int]: large 1M\n");
        total_fail++;
    }
    free(a);
}

static int cmp_float(const void *a, const void *b)
{
    float x = *(const float *)a, y = *(const float *)b;
    return (x > y) - (x < y);
}

static void check_float(const char *name, float *arr, int n)
{
    float *expected = malloc(n * sizeof(float));
    memcpy(expected, arr, n * sizeof(float));
    qsort(expected, n, sizeof(float), cmp_float);

    merge_sort_array_float(arr, n);

    if (memcmp(arr, expected, n * sizeof(float)) != 0) {
        printf("FAIL [float]: %s (n=%d)\n", name, n);
        if (n <= 40) {
            printf("  Got:      ");
            for (int i = 0; i < n; i++) printf("%.4f ", arr[i]);
            printf("\n  Expected: ");
            for (int i = 0; i < n; i++) printf("%.4f ", expected[i]);
            printf("\n");
        }
        total_fail++;
    } else {
        total_pass++;
    }
    free(expected);
}

static void test_float_edge_cases(void)
{
    merge_sort_array_float(NULL, 0);
    total_pass++;

    float a1[] = {3.14f};
    check_float("single", a1, 1);

    float a2[] = {2.0f, 1.0f};
    check_float("two reversed", a2, 2);

    float a3[] = {1.0f, 2.0f};
    check_float("two sorted", a3, 2);

    float a4[] = {5.5f, 5.5f};
    check_float("two equal", a4, 2);
}

static void test_float_patterns(void)
{
    float a[] = {0.1f, 0.2f, 0.3f, 0.4f, 0.5f, 0.6f, 0.7f, 0.8f};
    check_float("already sorted", a, 8);

    float b[] = {0.8f, 0.7f, 0.6f, 0.5f, 0.4f, 0.3f, 0.2f, 0.1f};
    check_float("reverse", b, 8);

    float c[50];
    for (int i = 0; i < 50; i++) c[i] = 7.7f;
    check_float("all equal", c, 50);

    float d[] = {-1.5f, 0.0f, 3.14f, -0.001f, 2.72f, -100.0f, 0.0f};
    check_float("mixed negatives", d, 7);

    float e[] = {FLT_MAX, -FLT_MAX, 0.0f, FLT_MIN, -FLT_MIN, 1.0f};
    check_float("FLT extremes", e, 6);
}

static void test_float_sizes(void)
{
    for (int n = 2; n <= 64; n++) {
        float *a = malloc(n * sizeof(float));
        for (int i = 0; i < n; i++) a[i] = (float)(n - i) + 0.5f;
        char name[32];
        snprintf(name, sizeof(name), "size %d", n);
        check_float(name, a, n);
        free(a);
    }
}

static void test_float_random(void)
{
    int sizes[] = {100, 256, 500, 1000, 4096, 10000, 50000, 100000};
    for (int s = 0; s < (int)(sizeof(sizes) / sizeof(sizes[0])); s++) {
        int n = sizes[s];
        float *a = malloc(n * sizeof(float));
        for (int i = 0; i < n; i++)
            a[i] = ((float)rand() / RAND_MAX) * 2000.0f - 1000.0f;
        char name[64];
        snprintf(name, sizeof(name), "random n=%d", n);
        check_float(name, a, n);
        free(a);
    }
}

static void test_float_preservation(void)
{
    int n = 1000;
    float *a = malloc(n * sizeof(float));
    float *b = malloc(n * sizeof(float));
    for (int i = 0; i < n; i++) a[i] = (float)(rand() % 20);
    memcpy(b, a, n * sizeof(float));
    qsort(b, n, sizeof(float), cmp_float);
    merge_sort_array_float(a, n);
    if (memcmp(a, b, n * sizeof(float)) == 0) {
        total_pass++;
    } else {
        printf("FAIL [float]: element preservation\n");
        total_fail++;
    }
    free(a);
    free(b);
}

static void test_float_large(void)
{
    int n = 1000000;
    float *a = malloc(n * sizeof(float));
    for (int i = 0; i < n; i++) a[i] = (float)rand() / RAND_MAX;
    clock_t t0 = clock();
    merge_sort_array_float(a, n);
    double ms = (double)(clock() - t0) / CLOCKS_PER_SEC * 1000.0;

    int ok = 1;
    for (int i = 1; i < n; i++)
        if (a[i] < a[i - 1]) { ok = 0; break; }

    if (ok) {
        printf("  float large (1M): %.1f ms - PASS\n", ms);
        total_pass++;
    } else {
        printf("FAIL [float]: large 1M\n");
        total_fail++;
    }
    free(a);
}

int main(void)
{
    srand(42);
    printf("Running merge sort tests (int + float)...\n\n");

    test_int_edge_cases();
    test_int_patterns();
    test_int_sizes();
    test_int_random();
    test_int_preservation();
    test_int_large();

    test_float_edge_cases();
    test_float_patterns();
    test_float_sizes();
    test_float_random();
    test_float_preservation();
    test_float_large();

    printf("\n=== Results: %d passed, %d failed ===\n", total_pass, total_fail);
    return total_fail > 0 ? 1 : 0;
}
