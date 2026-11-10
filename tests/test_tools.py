import unittest
from datetime import date
from classiccalc.mathlib import D,CalcError
from classiccalc.tools import UNITS,add_date,convert,date_difference,parse_date,solve_worksheet,mortgage_payment


class ConversionTests(unittest.TestCase):
    def test_categories(self):self.assertEqual(len(UNITS),11)
    def test_length(self):self.assertEqual(convert(D(1),'Length','Inches','Centimeters'),D('2.54'))
    def test_mile(self):self.assertEqual(convert(D(1),'Length','Miles','Meters'),D('1609.344'))
    def test_temp_freezing(self):self.assertLess(abs(convert(D(32),'Temperature','Degrees Fahrenheit','Degrees Celsius')),D('1e-50'))
    def test_temp_boiling(self):self.assertLess(abs(convert(D(100),'Temperature','Degrees Celsius','Degrees Fahrenheit')-212),D('1e-50'))
    def test_temp_kelvin(self):self.assertEqual(convert(D(0),'Temperature','Degrees Celsius','Kelvin'),D('273.15'))
    def test_volume_us(self):self.assertEqual(convert(D(1),'Volume','Gallons (US)','Liters'),D('3.785411784'))
    def test_volume_uk(self):self.assertEqual(convert(D(1),'Volume','Gallons (UK)','Liters'),D('4.54609'))
    def test_mass(self):self.assertEqual(convert(D(1),'Weight/Mass','Pounds','Kilograms'),D('.45359237'))
    def test_every_unit_roundtrip(self):
        for category,units in UNITS.items():
            base=next(iter(units))
            for name in units:
                with self.subTest(category=category,unit=name):
                    result=convert(convert(D('123.456'),category,name,base),category,base,name)
                    self.assertLess(abs(result-D('123.456')),D('1e-48'))
    def test_unknown(self):
        with self.assertRaises(CalcError):convert(D(1),'Nope','a','b')


class DateTests(unittest.TestCase):
    def test_days(self):self.assertEqual(date_difference(date(2024,1,1),date(2025,1,1))['total_days'],366)
    def test_reverse_absolute(self):self.assertEqual(date_difference(date(2025,1,1),date(2024,1,1))['total_days'],366)
    def test_month_end(self):self.assertEqual(add_date(date(2024,1,31),months=1),date(2024,2,29))
    def test_leap_year(self):self.assertEqual(add_date(date(2024,2,29),years=1),date(2025,2,28))
    def test_subtract(self):self.assertEqual(add_date(date(2024,3,31),months=-1),date(2024,2,29))
    def test_combined(self):self.assertEqual(add_date(date(2024,1,1),years=1,months=2,days=3),date(2025,3,4))
    def test_same(self):self.assertEqual(date_difference(date(2024,1,1),date(2024,1,1))['total_days'],0)
    def test_calendar_diff(self):
        r=date_difference(date(2020,1,1),date(2021,3,10));self.assertEqual((r['years'],r['months'],r['weeks'],r['days']),(1,2,1,2))
    def test_parse(self):self.assertEqual(parse_date('2024-02-29'),date(2024,2,29))
    def test_invalid_date(self):
        with self.assertRaises(CalcError):parse_date('2023-02-29')
    def test_range(self):
        with self.assertRaises(CalcError):add_date(date(9999,12,31),days=1)


class WorksheetTests(unittest.TestCase):
    def test_mortgage(self):
        r=solve_worksheet('Mortgage','payment',dict(purchase=D(250000),down=D(50000),years=D(30),rate=D(5)))
        self.assertLess(abs(r-D('1073.643246024277969656985158')),D('1e-20'))
    def test_zero_interest(self):self.assertEqual(mortgage_payment(D(120000),D(10),D(0)),1000)
    def test_mortgage_roundtrip(self):
        values=dict(purchase=D(250000),down=D(50000),years=D(30),rate=D(5))
        values['payment']=solve_worksheet('Mortgage','payment',values)
        for target in values:
            with self.subTest(target=target):
                result=solve_worksheet('Mortgage',target,{k:v for k,v in values.items() if k!=target})
                self.assertLess(abs(result-values[target]),D('1e-40'))
    def test_mortgage_insufficient_payment(self):
        with self.assertRaises(CalcError):solve_worksheet('Mortgage','years',dict(purchase=D(250000),down=D(50000),rate=D(5),payment=D(100)))
    def test_lease(self):
        self.assertEqual(solve_worksheet('Vehicle lease','payment',dict(purchase=D(30000),residual=D(18000),months=D(36),rate=D(6))),D(12000)/36+120)
    def test_lease_roundtrip(self):
        values=dict(purchase=D(30000),residual=D(18000),months=D(36),rate=D(6))
        values['payment']=solve_worksheet('Vehicle lease','payment',values)
        for target in values:
            with self.subTest(target=target):
                result=solve_worksheet('Vehicle lease',target,{k:v for k,v in values.items() if k!=target})
                self.assertLess(abs(result-values[target]),D('1e-40'))
    def test_mpg(self):self.assertEqual(solve_worksheet('Fuel economy (mpg)','economy',dict(distance=D(300),fuel=D(10))),30)
    def test_l100(self):self.assertEqual(solve_worksheet('Fuel economy (L/100 km)','economy',dict(distance=D(500),fuel=D(40))),8)
    def test_fuel_roundtrip(self):
        for name in ('Fuel economy (mpg)','Fuel economy (L/100 km)'):
            values=dict(distance=D(500),fuel=D(40));values['economy']=solve_worksheet(name,'economy',values)
            for target in values:self.assertEqual(solve_worksheet(name,target,{k:v for k,v in values.items() if k!=target}),values[target])
    def test_divide_zero(self):
        with self.assertRaises(CalcError):solve_worksheet('Fuel economy (mpg)','economy',dict(distance=D(300),fuel=D(0)))
    def test_negative(self):
        with self.assertRaises(CalcError):solve_worksheet('Fuel economy (mpg)','economy',dict(distance=D(-300),fuel=D(10)))
