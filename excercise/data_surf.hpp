#ifndef SURF_DATA_HPP
#define SURF_DATA_HPP

class LampSurfData
{
	explicit LampSurfData();
	float wave_height;
	float wave_period;
	size_t wind_speed;
	size_t wind_direction;
	std::string location;
	std::string timestamp; 
}

LampSurfData::LampSurfData() : wave_height(0), wave_period(0), wind_speed(0), wind_direction(0)  
{}

#endif //SURF_DATA_HPP
