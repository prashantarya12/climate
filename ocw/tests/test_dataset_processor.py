#
#  Licensed to the Apache Software Foundation (ASF) under one or more
#  contributor license agreements.  See the NOTICE file distributed with
#  this work for additional information regarding copyright ownership.
#  The ASF licenses this file to You under the Apache License, Version 2.0
#  (the "License"); you may not use this file except in compliance with
#  the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import unittest
import datetime
from ocw import dataset_processor as dp
from ocw import dataset as ds
import numpy as np
import numpy.ma as ma

class CustomAssertions:
    # Custom Assertions to handle Numpy Arrays
    def assert1DArraysEqual(self, array1, array2):
        self.assertSequenceEqual(tuple(array1), tuple(array2))

class TestEnsemble(unittest.TestCase, CustomAssertions): 
    def test_unequal_dataset_shapes(self):
        self.ten_year_dataset = ten_year_monthly_dataset()
        self.two_year_dataset = two_year_daily_dataset()
        with self.assertRaises(ValueError):
            self.ensemble_dataset = dp.ensemble([self.ten_year_dataset, self.two_year_dataset])
    
    def test_ensemble_logic(self):
        self.datasets = []
        self.datasets.append(build_ten_cube_dataset(1))
        self.datasets.append(build_ten_cube_dataset(2))
        self.three = build_ten_cube_dataset(3)
        self.datasets.append(self.three)
        self.datasets.append(build_ten_cube_dataset(4))
        self.datasets.append(build_ten_cube_dataset(5))
        self.ensemble = dp.ensemble(self.datasets)
        self.ensemble_flat = self.ensemble.values.flatten()
        self.three_flat = self.three.values.flatten()
        self.assert1DArraysEqual(self.ensemble_flat, self.three_flat)
    
    def test_ensemble_name(self):
        self.ensemble_dataset_name = "Dataset Ensemble"
        self.datasets = []
        self.datasets.append(build_ten_cube_dataset(1))
        self.datasets.append(build_ten_cube_dataset(2))
        self.ensemble = dp.ensemble(self.datasets)
        self.assertEquals(self.ensemble.name, self.ensemble_dataset_name)
        

class TestTemporalRebin(unittest.TestCase, CustomAssertions):
    
    def setUp(self):
        self.ten_year_monthly_dataset = ten_year_monthly_dataset()
        self.ten_year_annual_times = np.array([datetime.datetime(year, 1, 1) for year in range(2000, 2010)])
        self.two_years_daily_dataset = two_year_daily_dataset()
    
    def test_monthly_to_annual_rebin(self):
        annual_dataset = dp.temporal_rebin(self.ten_year_monthly_dataset, datetime.timedelta(days=365))
        self.assert1DArraysEqual(annual_dataset.times, self.ten_year_annual_times)
    
    def test_monthly_to_full_rebin(self):
        full_dataset = dp.temporal_rebin(self.ten_year_monthly_dataset, datetime.timedelta(days=3650))
        full_times = [datetime.datetime(2004, 12, 16)]
        self.assertEqual(full_dataset.times, full_times)
    
    def test_daily_to_monthly_rebin(self):
        """This test takes a really long time to run.  TODO: Figure out where the performance drag is"""
        monthly_dataset = dp.temporal_rebin(self.two_years_daily_dataset, datetime.timedelta(days=31))
        bins = list(set([datetime.datetime(time_reading.year, time_reading.month, 1) for time_reading in self.two_years_daily_dataset.times]))
        bins = np.array(bins)
        bins.sort()
        self.assert1DArraysEqual(monthly_dataset.times, bins)
    
    def test_daily_to_annual_rebin(self):
        annual_dataset = dp.temporal_rebin(self.two_years_daily_dataset, datetime.timedelta(days=366))
        bins = list(set([datetime.datetime(time_reading.year, 1, 1) for time_reading in self.two_years_daily_dataset.times]))
        bins = np.array(bins)
        bins.sort()
        self.assert1DArraysEqual(annual_dataset.times, bins)
        
    
    def test_non_rebin(self):
        """This will take a monthly dataset and ask for a monthly rebin of 28 days.  The resulting
        dataset should have the same time values"""
        monthly_dataset = dp.temporal_rebin(self.ten_year_monthly_dataset, datetime.timedelta(days=28))
        good_times = self.ten_year_monthly_dataset.times
        self.assert1DArraysEqual(monthly_dataset.times, good_times)


class TestRcmesSpatialRegrid(unittest.TestCase):

    def test_return_array_shape(self):
        spatial_values = np.ones([90,180])
        spatial_values = ma.array(spatial_values)
        
        lat_range = ma.array(range(-89, 90, 2))
        lon_range = ma.array(range(-179, 180, 2))
        
        lons, lats = np.meshgrid(lon_range, lat_range)
        # Convert these to masked arrays
        lats = ma.array(lats)
        lons = ma.array(lons)
        
        lat2_range = np.array(range(-89, 90, 4))
        lon2_range = np.array(range(-179, 180, 4))
        
        lons2, lats2 = np.meshgrid(lon2_range, lat2_range)
        # Convert to masked arrays
        lats2 = ma.array(lats2)
        lons2 = ma.array(lons2)

        regridded_values = dp._rcmes_spatial_regrid(spatial_values, lats, lons, lats2, lons2)
        self.assertEqual(regridded_values.shape, lats2.shape)
        self.assertEqual(regridded_values.shape, lons2.shape)

class TestSpatialRegrid(unittest.TestCase, CustomAssertions):
    
    def setUp(self):
        self.input_dataset = ten_year_monthly_dataset()
        self.new_lats = np.array(range(-89, 90, 4))
        self.new_lons = np.array(range(-179, 180, 4))
        self.regridded_dataset = dp.spatial_regrid(self.input_dataset, self.new_lats, self.new_lons)


    def test_returned_lats(self):
        self.assert1DArraysEqual(self.regridded_dataset.lats, self.new_lats)

    def test_returned_lons(self):
        self.assert1DArraysEqual(self.regridded_dataset.lons, self.new_lons)

    def test_shape_of_values(self):
        regridded_data_shape = self.regridded_dataset.values.shape
        expected_data_shape = (len(self.input_dataset.times), len(self.new_lats), len(self.new_lons))
        self.assertSequenceEqual(regridded_data_shape, expected_data_shape)

class TestSubset(unittest.TestCase):
    def test_subset(self):
        target_dataset = ten_year_monthly_dataset()

        subregion = {
            'latMin': -81,
            'latMax': 81,
            'lonMin': -161,
            'lonMax': 161,
            'start': datetime.datetime(2001, 1, 1),
            'end': datetime.datetime(2004, 1, 1)
        }

        subset = dp.subset(subregion, target_dataset)
        self.assertEqual(subset.lats.shape[0], 82)
        self.assertEqual(subset.lons.shape[0], 162)
        self.assertEqual(subset.times.shape[0], 37)
        self.assertEqual(subset.values.shape, (37, 82, 162))

def ten_year_monthly_dataset():
    lats = np.array(range(-89, 90, 2))
    lons = np.array(range(-179, 180, 2))
    # Ten Years of monthly data
    times = np.array([datetime.datetime(year, month, 1) for year in range(2000, 2010) for month in range(1, 13)])
    values = np.ones([len(times), len(lats), len(lons)])
    input_dataset = ds.Dataset(lats, lons, times, values, variable="test variable name")
    return input_dataset

def two_year_daily_dataset():
    lats = np.array(range(-89, 90, 2))
    lons = np.array(range(-179, 180, 2))
    times = np.array([datetime.datetime(2001, 1, 1) + datetime.timedelta(days=d) for d in range(730)])
    values = np.ones([len(times), len(lats), len(lons)])
    dataset = ds.Dataset(lats, lons, times, values, variable='random data')
    return dataset    

def build_ten_cube_dataset(value):
    lats = np.array(range(-89, 90, 18))
    lons = np.array(range(-179, 180, 36))
    times = np.array([datetime.datetime(year, 1, 1) for year in range(2000, 2010)])
    values = np.ones([len(times), len(lats), len(lons)])
    values = values * value
    dataset = ds.Dataset(lats, lons, times, values)
    return dataset
    


if __name__ == '__main__':
    unittest.main()