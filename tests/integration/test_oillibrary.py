#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of OpenDrift.
#
# OpenDrift is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2
#
# OpenDrift is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenDrift.  If not, see <https://www.gnu.org/licenses/>.
#
# Copyright 2015, Knut-Frode Dagestad, MET Norway

import os
import unittest
import logging
from datetime import datetime, timedelta

import numpy as np

from opendrift.models.openoil import OpenOil

try:
    from oil_library import get_oil_props
    has_oil_library = True
except Exception as e:
    has_oil_library = False

class TestOil(unittest.TestCase):
    """Tests for OilLibrary"""

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_oils(self):
        o = OpenOil(loglevel=50, weathering_model='noaa')

        assert len(o.oiltypes) >= 1478

        for oiltype in o.oiltypes[12:14]:
            if oiltype == 'JP-8':
                continue
            o = OpenOil(loglevel=50, weathering_model='noaa')
            o.set_config('environment:fallback:x_wind', 7)
            o.set_config('environment:fallback:y_wind', 0)
            o.set_config('environment:fallback:x_sea_water_velocity', .7)
            o.set_config('environment:fallback:y_sea_water_velocity', 0)
            o.set_config('environment:fallback:land_binary_mask', 0)
            o.seed_elements(4.7, 60.0, radius=3000, number=3, z=0,
            time=datetime.now(), oiltype=oiltype)
            o.set_config('processes:evaporation', True)
            o.set_config('processes:emulsification', True)
            o.set_config('drift:vertical_mixing', False)
            o.set_config('drift:wind_uncertainty', 0)
            o.set_config('drift:current_uncertainty', 0)
            o.run(steps=3)
            initial_mass = o.get_property('mass_oil')[0][0, 0]
            self.assertEqual(o.elements.mass_evaporated.min(),
                             o.elements.mass_evaporated.max())
            self.assertTrue(o.elements.mass_evaporated.min() > 0)
            self.assertTrue(o.elements.mass_evaporated.max()/initial_mass <= 1)
            print(oiltype, o.elements.mass_evaporated.min())

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_oilbudget(self):
        for windspeed in [3, 8]:
            for dispersion in [True, False]:
                o = OpenOil(loglevel=30, weathering_model='noaa')
                o.set_config('environment:fallback:x_wind', windspeed)
                o.set_config('environment:fallback:y_wind', 0)
                o.set_config('environment:fallback:x_sea_water_velocity', 0)
                o.set_config('environment:fallback:y_sea_water_velocity', 0)
                o.set_config('environment:fallback:land_binary_mask', 0)
                o.set_config('seed:oil_type', 'SIRTICA')
                o.set_config('processes:dispersion', dispersion)
                seed_hours=3
                m3_per_hour=200
                o.set_config('seed:m3_per_hour', m3_per_hour)
                o.seed_elements(lon=0, lat=60, number=100,
                                #m3_per_hour=m3_per_hour,
                                time=[datetime.now(),
                                      datetime.now() +
                                        timedelta(hours=seed_hours)])
                o.run(duration=timedelta(hours=4))
                b = o.get_oil_budget()
                density = o.get_property('density')[0][0,0]
                volume = b['mass_total']/density
                self.assertAlmostEqual(volume[-1],
                                       seed_hours*m3_per_hour, 2)

                if dispersion is True:
                    disp='dispersion'
                else:
                    disp='nodispersion'
                filename = 'oilbudget_%s_%s.png' % (windspeed, disp)
                o.plot_oil_budget(filename=filename)
                os.remove(filename)

    def test_oil_volume(self):
        o = OpenOil(loglevel=50)
        m3_per_hour=50
        o.set_config('seed:m3_per_hour', m3_per_hour)
        o.seed_elements(lon=4, lat=60, time=datetime.now())
        o.set_config('environment:fallback:x_wind', 0)
        o.set_config('environment:fallback:y_wind', 0)
        o.set_config('environment:fallback:x_sea_water_velocity', 0)
        o.set_config('environment:fallback:y_sea_water_velocity', 0)
        o.set_config('environment:fallback:land_binary_mask', 0)
        o.run(steps=1)
        b = o.get_oil_budget()
        volume = b['mass_total']/b['oil_density']
        self.assertEqual(volume[0], m3_per_hour)
        self.assertEqual(volume[1], m3_per_hour)

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_dispersion(self):
        for oil in ['SMORBUKK KONDENSAT', 'SKRUGARD']:
            for windspeed in [3, 8]:
                if oil == 'SKRUGARD' and windspeed == 3:
                    continue
                o = OpenOil(loglevel=20, weathering_model='noaa')
                oilname = oil
                if oil not in o.oiltypes:
                    if oilname == 'SKRUGARD':
                        oilname = 'SKRUGARD 2012'
                    elif oilname == 'SMORBUKK KONDENSAT':
                        oilname = 'SMORBUKK KONDENSAT 2003'
                o.seed_elements(lon=4.8, lat=60, number=100,
                                time=datetime.now(), oiltype=oilname)
                o.set_config('processes:dispersion', True)
                o.set_config('vertical_mixing:timestep', 10)
                o.set_config('environment:fallback:land_binary_mask', 0)
                o.set_config('environment:fallback:x_wind', windspeed)
                o.set_config('environment:fallback:y_wind', 0)
                o.set_config('environment:fallback:x_sea_water_velocity', 0)
                o.set_config('environment:fallback:y_sea_water_velocity', .3)
                o.run(duration=timedelta(hours=3), time_step=900)

                b = o.get_oil_budget()
                actual_dispersed = b['mass_dispersed']/b['mass_total']
                actual_submerged = b['mass_submerged']/b['mass_total']
                actual_evaporated = b['mass_evaporated']/b['mass_total']
                print('Dispersion fraction %f for '
                      '%s and wind speed %f' %
                      (actual_dispersed[-1], oil, windspeed))
                if oil == 'SMORBUKK KONDENSAT' and windspeed == 3:
                    fraction_dispersed = 0
                    fraction_submerged = 0
                    fraction_evaporated = 0.526
                    meanlon = 4.81742
                elif oil == 'SMORBUKK KONDENSAT' and windspeed == 8:
                    fraction_dispersed = 0.086
                    fraction_submerged = 0.372
                    fraction_evaporated = 0.479
                    meanlon = 4.811
                elif oil == 'SKRUGARD' and windspeed == 8:
                    fraction_dispersed = 0.139
                    fraction_submerged = 0.367
                    fraction_evaporated = 0.180
                    meanlon = 4.824
                else:
                    fraction_dispersed = -1  # not defined
                self.assertAlmostEqual(actual_dispersed[-1],
                                       fraction_dispersed, 2)
                self.assertAlmostEqual(actual_submerged[-1],
                                       fraction_submerged, 2)
                self.assertAlmostEqual(actual_evaporated[-1],
                                       fraction_evaporated, 2)
                self.assertAlmostEqual(np.mean(o.elements.lon), meanlon, 3)
                #o.plot_oil_budget()

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_no_dispersion(self):
        o = OpenOil(loglevel=50, weathering_model='noaa')

        o.seed_elements(lon=4.8, lat=60, number=100,
                        time=datetime.now(), oiltype='SIRTICA')
        o.set_config('processes:dispersion', False)
        o.set_config('environment:fallback:land_binary_mask', 0)
        o.set_config('environment:fallback:x_wind', 8)
        o.set_config('environment:fallback:y_wind', 8)
        o.set_config('environment:fallback:x_sea_water_velocity', 0)
        o.set_config('environment:fallback:y_sea_water_velocity', .3)
        o.run(duration=timedelta(hours=2), time_step=1800)
        b = o.get_oil_budget()
        actual_dispersed = b['mass_dispersed']/b['mass_total']
        self.assertAlmostEqual(actual_dispersed[-1], 0)
        self.assertIsNone(np.testing.assert_array_almost_equal(
            o.elements.lon[0:3], [4.797, 4.802 , 4.826], 3))

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_biodegradation(self):
        o = OpenOil(loglevel=50, weathering_model='noaa')

        o.seed_elements(lon=4.8, lat=60, number=100,
                        time=datetime.now(), oiltype='SIRTICA')
        o.set_config('processes:dispersion', True)
        o.set_config('processes:evaporation', True)
        o.set_config('processes:emulsification', True)
        o.set_config('processes:biodegradation', True)
        o.set_config('environment:fallback:land_binary_mask', 0)
        o.set_config('environment:fallback:x_wind', 0)
        o.set_config('environment:fallback:y_wind', 0)
        o.set_config('environment:fallback:x_sea_water_velocity', 0)
        o.set_config('environment:fallback:y_sea_water_velocity', 0)
        o.set_config('environment:fallback:sea_water_temperature', 30)
        o.run(duration=timedelta(days=1), time_step=1800)
        initial_mass = o.get_property('mass_oil')[0][0, 0]
        biodegraded30 = o.elements.mass_biodegraded
        factor = 0.127 #(1-e^(-1))
        self.assertAlmostEqual(biodegraded30[-1]/initial_mass, factor, 3)

    @unittest.skipIf(has_oil_library is False,
                     'NOAA OilLibrary is needed')
    def test_droplet_distribution(self):
        # TODO: Should also add Li2017 here
        for droplet_distribution in ['Johansen et al. (2015)']:
            o = OpenOil(loglevel=50, weathering_model='noaa')
            if 'SKRUGARD' in o.oiltypes:
                oiltype = 'SKRUGARD'
            else:
                oiltype = 'SKRUGARD 2012'
            o.set_config('wave_entrainment:droplet_size_distribution',
                         droplet_distribution)
            o.seed_elements(lon=4.8, lat=60, number=100,
                            time=datetime.now(), oiltype=oiltype)
            o.set_config('environment:fallback:land_binary_mask', 0)
            o.set_config('environment:fallback:x_wind', 8)
            o.set_config('environment:fallback:y_wind', 0)
            o.set_config('environment:fallback:x_sea_water_velocity', 0)
            o.set_config('environment:fallback:y_sea_water_velocity', .3)
            o.run(duration=timedelta(hours=1), time_step=1800)
            d = o.elements.diameter
            # Suspicious, Sintef-param should give larer droplets
            if droplet_distribution == 'Johansen et al. (2015)':
                #self.assertAlmostEqual(d.mean(), 0.000072158)
                self.assertAlmostEqual(d.mean(), 0.000653, 2)


if __name__ == '__main__':
    unittest.main()
