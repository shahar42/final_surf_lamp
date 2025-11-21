#ifndef SURF_ANALIZER_HPP
#define SURF_ANALIZER_HPP

#include <string>
#include "data_surf.hpp"

class SurfAnalizer
{
	SurfAnalizer();
	virtual ~SurfAnalizer();
	virtual void do_analize()=0;
	virtual std::string get_report()=0;
	virtual std::string analizer_name()=0;
protected:
	const std::string report();
};

#endif //SURF_ANALIZER_HPP


