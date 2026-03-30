#ifndef MY_LINEAR_BUFFER_HPP
#define MY_LINEAR_BUFFER_HPP

#include "mutex_lock.hpp"

template<typename T, size_t Size>                                                                                                                                                            
class LinearBuff 
{
public:    
    LinearBuff() : m_offset(0){}
    ~LinearBuff() = default;

    LinearBuff(const LinearBuff&) = delete;  
    LinearBuff& operator=(const LinearBuff&) = delete;
    
    T buffer[Size];
    size_t m_offset;
                                                                                                                                         
};      

class AsyncSerialLogger
{
public:
    explicit AsyncSerialLogger()
    {
        m_mutex = xSemaphoreCreateMutex();
    }
    ~AsyncSerialLogger()
    {
        vSemaphoreDelete(m_mutex);
    }
    void Log(const char* msg);

    void Flush();
private:
    LinearBuff<char, 2048> buff;
    SemaphoreHandle_t m_mutex;
};

void AsyncSerialLogger::Log(const char* msg)
{
    MutexGuard lockit(m_mutex);
    char* startidx = buff.buffer + buff.m_offset;
    size_t len = strlen(msg) + 1;
    if(2048 - buff.m_offset < len)
    {
        Flush();
        startidx = buff.buffer;
    }
    memcpy(startidx, msg, len); 
    buff.m_offset = buff.m_offset + len; 
    buff.buffer[buff.m_offset - 1] = '\n';  

}

void AsyncSerialLogger::Flush()
{
    if (buff.m_offset > 0)
    {
        Serial.write(buff.buffer, buff.m_offset);
        buff.m_offset = 0;
    }
}

#endif // MY_LINEAR_BUFFER_HPP

