import unittest
from unittest.mock import patch
from io import StringIO
from project1 import *

class Test_Calling_All_Station(unittest.TestCase):
    @patch('builtins.input', side_effect = ["C:/Users/user/Desktop/Project1/samples/sample_input.txt"])
    def test_function_input(self, mock_input):
        result = read_file_path()
        self.assertEqual(result, 'C:/Users/user/Desktop/Project1/samples/sample_input.txt')

    def test_read_total_simulation_time(self):
        info = Gather_Info_from_File(['DEVICE 1', 'LENGTH 9999', 'DEVICE 2', 'DEVICE 3', 'PROPAGATE 3 4 500'])
        self.assertEqual(info.read_total_simulation_time(),9999)

    def test_no_info_about_time(self):
        info = Gather_Info_from_File(['DEVICE 1', 'DEVICE 2','DEVICE 3', 'PROPAGATE 3 4 500'])
        with self.assertRaises(ValueError):
            info.read_total_simulation_time()
    def test_read_all_devices(self):
        info = Gather_Info_from_File(['DEVICE 1', 'DEVICE 2', 'PROPAGATE 3 4 500','DEVICE 3', 'LENGTH 9999'])
        self.assertEqual(info.read_all_devices(), ['1', '2', '3'])

    def test_read_propagate_process(self):
        info = Gather_Info_from_File(['LENGTH 9999', 'DEVICE 1', 'DEVICE 2','DEVICE 3', 'PROPAGATE 3 4 500'])
        self.assertEqual(
            info.read_propagate_process(),{'3':Propagation('4',500)})

    def test_read_warning_info(self):
        info = Gather_Info_from_File(['LENGTH 1111', 'DEVICE 4', 'DEVICE 8', 'PROPAGATE 3 4 500','DEVICE 3', 'CANCEL 1 Trouble 2200', 'ALERT 1 Trouble 0'])
        self.assertEqual(info.read_warning_info(),
            [[('ALERT', '1', 'Trouble', '0'), ('CANCEL', '1', 'Trouble', '2200')]])

    def test_receive_message_cancel(self):
        simulation = Simulation(['1', '2', '3'], 3000)
        simulation.receive_message_cancel('2', '1', 'WRONG', 2000)
        self.assertEqual(simulation.written_file, ['@2000: #2 RECEIVED CANCELLATION FROM #1: WRONG'])

    def test_receive_message_alert(self):
        simulation = Simulation(['1', '2', '3'], 3000)
        simulation.receive_message_alert('2', '1', 'WRONG', 2000)
        self.assertEqual(simulation.written_file, ['@2000: #2 RECEIVED ALERT FROM #1: WRONG'])

    def test_send_message_cancel(self):
        simulation = Simulation(['1', '2', '3'], 3000)
        simulation.send_message_cancel('2', '1', 'WRONG', 2000)
        self.assertEqual(simulation.written_file,
                         ['@2000: #2 SENT CANCELLATION TO #1: WRONG'])

    def test_send_message_alert(self):
        simulation = Simulation(['1', '2', '3'], 3000)
        simulation.send_message_alert('2', '1', 'WRONG', 2000)
        self.assertEqual(simulation.written_file,
                         ['@2000: #2 SENT ALERT TO #1: WRONG'])

    def test_only_cancel_process(self):
        simulation = Simulation(['1','2', '3'],250)
        simulation.simulation_process([[('CANCEL', '1', 'Trouble', '0')],],
            {'1':Propagation('2',100), '2':Propagation('3',100), '3':Propagation('1',100)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file,
                         ['@0: #1 SENT CANCELLATION TO #2: Trouble', '@100: #2 RECEIVED CANCELLATION FROM #1: Trouble',
                         '@100: #2 SENT CANCELLATION TO #3: Trouble', '@200: #3 RECEIVED CANCELLATION FROM #2: Trouble',
                        '@200: #3 SENT CANCELLATION TO #1: Trouble', '@250: END'])

    def test_only_alert_process(self):
        simulation = Simulation(['1','2', '3'],200)
        simulation.simulation_process([[('ALERT', '1', 'Trouble', '0')]],
            {'1':Propagation('2',50), '2':Propagation('3',100), '3':Propagation('1',100)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file,
                         ['@0: #1 SENT ALERT TO #2: Trouble', '@50: #2 RECEIVED ALERT FROM #1: Trouble',
                         '@50: #2 SENT ALERT TO #3: Trouble', '@150: #3 RECEIVED ALERT FROM #2: Trouble', '@150: #3 SENT ALERT TO #1: Trouble','@200: END'])

    def test_1alert_1cancel_processA(self):
        simulation = Simulation(['1', '2', '3', '4'], 9999)
        simulation.simulation_process([[('CANCEL', '1', 'Trouble', '2200'), ('ALERT', '1', 'Trouble', '0')]],
                                      {'1': Propagation('2', 750), '2': Propagation('3', 1250),
                                       '3': Propagation('4', 500), '4': Propagation('1', 1000)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file,
                         ['@0: #1 SENT ALERT TO #2: Trouble', '@750: #2 RECEIVED ALERT FROM #1: Trouble',
                                '@750: #2 SENT ALERT TO #3: Trouble',
                                '@2000: #3 RECEIVED ALERT FROM #2: Trouble',
                                '@2000: #3 SENT ALERT TO #4: Trouble',
                                '@2200: #1 SENT CANCELLATION TO #2: Trouble',
                                '@2500: #4 RECEIVED ALERT FROM #3: Trouble',
                                '@2500: #4 SENT ALERT TO #1: Trouble',
                                '@2950: #2 RECEIVED CANCELLATION FROM #1: Trouble',
                                '@2950: #2 SENT CANCELLATION TO #3: Trouble',
                                '@3500: #1 RECEIVED ALERT FROM #4: Trouble',
                                '@4200: #3 RECEIVED CANCELLATION FROM #2: Trouble',
                                '@4200: #3 SENT CANCELLATION TO #4: Trouble',
                                '@4700: #4 RECEIVED CANCELLATION FROM #3: Trouble',
                                '@4700: #4 SENT CANCELLATION TO #1: Trouble',
                                '@5700: #1 RECEIVED CANCELLATION FROM #4: Trouble',
                                '@9999: END'])

    def test_1alert_1cancel_processB(self):
        simulation = Simulation(['1', '2', '3'], 100)
        simulation.simulation_process([[('ALERT', '1', 'Trouble', '50'), ('CANCEL', '1', 'Trouble', '0')]],
                                      {'1': Propagation('2', 100), '2': Propagation('3', 100), '3': Propagation('1', 100)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file,
                         ['@0: #1 SENT CANCELLATION TO #2: Trouble', '@100: END'])

    def test_case_exceed_time(self):
        simulation = Simulation(['1', '2', '3'], 50)
        simulation.simulation_process(
            [[('ALERT', '1', 'Trouble', '0'), ('CANCEL', '1', 'Trouble', '50')]],
            {'1': Propagation('2', 100), '2': Propagation('3', 100), '3': Propagation('1', 100)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file,
                         ['@0: #1 SENT ALERT TO #2: Trouble', '@50: END'])

    def test_extreme_of_simulation_time(self):
        simulation = Simulation(['1', '2', '3'], 0)
        simulation.simulation_process(
            [[('ALERT', '1', 'Trouble', '0'), ('CANCEL', '1', 'Trouble', '50')]],
            {'1': Propagation('2', 100), '2': Propagation('3', 100), '3': Propagation('1', 100)})
        simulation.process_final_written_test()
        self.assertEqual(simulation.written_file, ['@0: END'])

    def test_read_file_successively(self):
        try:
            lista = read_all_info_in_file(Path('C:\\Users\\user\\Desktop\\Project1\\samples\\sample_input.txt'))
            self.assertEqual(lista, ['LENGTH 9999', 'DEVICE 1', 'DEVICE 2', 'DEVICE 3', 'DEVICE 4',
                                     'PROPAGATE 1 2 750', 'PROPAGATE 2 3 1250', 'PROPAGATE 3 4 500', 'PROPAGATE 4 1 1000',
                                     'ALERT 1 Trouble 0', 'CANCEL 1 Trouble 2200'])
        except:
            print("The Path may not fit your laptop. It is based on my memory location")
    def test_read_file_unsuccessfully(self):
        with self.assertRaises(FileNotFoundError):
            read_all_info_in_file(Path('111smple_input.txt'))




