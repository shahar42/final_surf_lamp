#ifndef MUTEX_LOCK_HPP
#define MUTEX_LOCK_HPP

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

class MutexGuard
{
public:
    explicit MutexGuard(SemaphoreHandle_t mutex, TickType_t timeout = portMAX_DELAY)
        : m_mutex(mutex), m_isLocked(false)
    {
        if (m_mutex != nullptr) {
            m_isLocked = (xSemaphoreTake(m_mutex, timeout) == pdTRUE);
        }
    }

    ~MutexGuard()
    {
        if (m_isLocked && m_mutex != nullptr) {
            xSemaphoreGive(m_mutex);
        }
    }

    bool isLocked() const { return m_isLocked; }

    // Disable copy and move
    MutexGuard(const MutexGuard&) = delete;
    MutexGuard& operator=(const MutexGuard&) = delete;
    MutexGuard(MutexGuard&&) = delete;
    MutexGuard& operator=(MutexGuard&&) = delete;

private:
    SemaphoreHandle_t m_mutex;
    bool m_isLocked;
};

#endif // MUTEX_LOCK_HPP