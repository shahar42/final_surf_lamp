#ifndef SEMPHR_H
#define SEMPHR_H

typedef void* SemaphoreHandle_t;

#define pdTRUE 1

inline SemaphoreHandle_t xSemaphoreCreateMutex() { return (void*)1; }
inline void vSemaphoreDelete(SemaphoreHandle_t) {}
inline int xSemaphoreTake(SemaphoreHandle_t, TickType_t) { return pdTRUE; }
inline int xSemaphoreGive(SemaphoreHandle_t) { return pdTRUE; }

#endif
