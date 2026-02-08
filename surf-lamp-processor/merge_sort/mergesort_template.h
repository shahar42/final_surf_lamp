#ifndef SORT_TYPE
#error "Define SORT_TYPE before including mergesort_template.h"
#endif
#ifndef SORT_SUFFIX
#error "Define SORT_SUFFIX before including mergesort_template.h"
#endif

#include <math.h>

#ifndef SORT_LE
#define SORT_LE(a,b) ((a) <= (b))
#endif
#ifndef SORT_GT
#define SORT_GT(a,b) ((a) > (b))
#endif

#define CONCAT2(a, b)      a##_##b
#define CONCAT(a, b)       CONCAT2(a, b)
#define FN(name)           CONCAT(name, SORT_SUFFIX)

#define INSERTION_THRESHOLD 32



static void FN(swap)(SORT_TYPE *a, SORT_TYPE *b)
{
    SORT_TYPE t = *a;
    *a = *b;
    *b = t;
}

static void FN(swap_block)(SORT_TYPE arr[], int a, int b, int len)
{
    for (int i = 0; i < len; i++)
        FN(swap)(&arr[a + i], &arr[b + i]);
}

static void FN(insertion_sort)(SORT_TYPE arr[], int lo, int hi)
{
    for (int i = lo + 1; i <= hi; i++) {
        SORT_TYPE val = arr[i];
        int j = i - 1;
        while (j >= lo && SORT_GT(arr[j], val)) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = val;
    }
}

static void FN(merge_with_buffer)(SORT_TYPE arr[], int lo, int mid, int hi,
                                  int buf)
{
    int len1 = mid - lo + 1;

    for (int i = 0; i < len1; i++)
        FN(swap)(&arr[lo + i], &arr[buf + i]);

    int p1 = buf;
    int e1 = buf + len1;
    int p2 = mid + 1;
    int e2 = hi + 1;
    int dst = lo;

    while (p1 < e1 && p2 < e2) {
        if (SORT_LE(arr[p1], arr[p2])) {
            FN(swap)(&arr[dst], &arr[p1]);
            p1++;
        } else {
            FN(swap)(&arr[dst], &arr[p2]);
            p2++;
        }
        dst++;
    }
    while (p1 < e1) {
        FN(swap)(&arr[dst], &arr[p1]);
        p1++;
        dst++;
    }
}

static void FN(inplace_merge)(SORT_TYPE arr[], int lo, int mid, int hi)
{
    int n = hi - lo + 1;

    if (SORT_LE(arr[mid], arr[mid + 1]))
        return;

    if (n <= INSERTION_THRESHOLD) {
        FN(insertion_sort)(arr, lo, hi);
        return;
    }

    int s = (int)sqrt((double)n);
    if (s < 2) s = 2;

    {
        int left = mid;
        int right = hi;
        int dest = hi;
        int count = s;

        while (count > 0) {
            if (left < lo) {
                if (right != dest) FN(swap)(&arr[dest], &arr[right]);
                right--;
            } else if (right <= mid) {
                if (left != dest) FN(swap)(&arr[dest], &arr[left]);
                left--;
            } else if (SORT_LE(arr[right], arr[left])) {
                if (left != dest) FN(swap)(&arr[dest], &arr[left]);
                left--;
            } else {
                if (right != dest) FN(swap)(&arr[dest], &arr[right]);
                right--;
            }
            dest--;
            count--;
        }
    }

    int buf_start  = hi - s + 1;
    int data_end   = buf_start - 1;
    int data_len   = data_end - lo + 1;
    int num_blocks = data_len / s;
    int remainder  = data_len - num_blocks * s;

    int first_block = lo + remainder;

    for (int i = 0; i < num_blocks - 1; i++) {
        int min_idx = i;
        for (int j = i + 1; j < num_blocks; j++) {
            SORT_TYPE tail_j   = arr[first_block + (j + 1) * s - 1];
            SORT_TYPE tail_min = arr[first_block + (min_idx + 1) * s - 1];
            if (SORT_GT(tail_min, tail_j))
                min_idx = j;
        }
        if (min_idx != i)
            FN(swap_block)(arr,
                           first_block + i * s,
                           first_block + min_idx * s,
                           s);
    }

    if (remainder > 0 && num_blocks > 0)
        FN(insertion_sort)(arr, lo, first_block + s - 1);

    for (int i = 0; i < num_blocks - 1; i++) {
        int block_lo  = first_block + i * s;
        int block_mid = block_lo + s - 1;
        int block_hi  = block_mid + s;
        if (block_hi > data_end)
            block_hi = data_end;

        if (SORT_LE(arr[block_mid], arr[block_mid + 1]))
            continue;

        FN(merge_with_buffer)(arr, block_lo, block_mid, block_hi, buf_start);
    }

    FN(insertion_sort)(arr, buf_start, hi);
    FN(insertion_sort)(arr, lo, hi);
}

void FN(merge_sort)(SORT_TYPE arr[], int lo, int hi)
{
    if (hi - lo + 1 <= INSERTION_THRESHOLD) {
        if (lo < hi)
            FN(insertion_sort)(arr, lo, hi);
        return;
    }

    int mid = lo + (hi - lo) / 2;
    FN(merge_sort)(arr, lo, mid);
    FN(merge_sort)(arr, mid + 1, hi);
    FN(inplace_merge)(arr, lo, mid, hi);
}

void FN(merge_sort_array)(SORT_TYPE arr[], int n)
{
    if (n > 1)
        FN(merge_sort)(arr, 0, n - 1);
}

#undef SORT_TYPE
#undef SORT_SUFFIX
#undef SORT_LE
#undef SORT_GT
#undef FN
#undef CONCAT
#undef CONCAT2
#undef INSERTION_THRESHOLD
