#include <stdio.h>
#include "threshold_calc.h"

int main(void)
{
    float result = 0;
    
    // Test 1: Within range
    result = ThreshCalculator(2.3f, 5.0f, 10.0f);
    printf("Test 1 (Within): should return <5.00> and we got %.2f \n", result);

    // Test 2: Above max
    result = ThreshCalculator(13.0f, 5.0f, 10.0f);
    printf("Test 2 (Above): should return <9999.00> and we got %.2f \n", result);

    // Test 3: Below min
    result = ThreshCalculator(4.0f, 5.6f, 10.1f);
    printf("Test 3 (Below): should return <5.60> and we got %.2f \n", result);

    return 0;
}
