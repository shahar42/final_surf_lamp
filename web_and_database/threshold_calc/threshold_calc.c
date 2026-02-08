#include <assert.h>
#include "threshold_calc.h"

// Threshold Calculator - Implementation
// High-performance C implementation for Arduino threshold logic
#define IMPOSIBBLE_THRESH 9999.0f

float ThreshCalculator(float curr_value, float user_min, float user_max)
{
    if(curr_value == -1.0f || user_max == -1.0f)
    {
        return user_min;
    }
    // If current value is higher than max, it's "impossible" to reach the threshold today
    if (curr_value > user_max)
    {
        return IMPOSIBBLE_THRESH;
    }
    

    // Otherwise, we return the user_min as the effective threshold
    // (This matches the logic of returning user_min if within range or below)
    return user_min;
}