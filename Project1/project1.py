from pathlib import Path
from collections import namedtuple
Propagation = namedtuple('Propagation', ['send_to', 'delay'])

def read_file_path():
    path = input()
    return path

def read_all_info_in_file(path) -> list:
    return_list = []
    try:
        # overwrite the input
        with open(Path(path), 'r') as f:
            content = f.readlines()
            for row in content:
                if row and row != '\n' and row[0] != '#':
                    return_list.append(row)
        processed_list = [element.strip() for element in return_list]
        return processed_list
    except:
        print('FILE NOT FOUND')
        raise FileNotFoundError



class Gather_Info_from_File:
    def __init__(self, info_extracted):
        self.list_of_setting = info_extracted
    def read_total_simulation_time(self) -> int:
        """The function would extract the information about the total simulation time
        and return as integer"""
        total_simulation_time = -1
        for ele in self.list_of_setting:
            if ele.split()[0] == 'LENGTH':
                total_simulation_time = int(ele.split()[1])
                break
        if total_simulation_time == -1:
            raise ValueError
        return total_simulation_time


    def read_all_devices(self) -> list:
        """The return list would cover all devices corresponding num as ['1', '2']"""
        all_device = []
        for ele in self.list_of_setting:
            if ele.split()[0] == 'DEVICE':
                all_device.append(ele.split()[1])
        return all_device

    def read_propagate_process(self) -> dict:
        """The return dictionary shows in following format as {device_num:Propagation(device-sent-to,delay)}
        for example as {'3':Propagation('4',500)}"""
        all_propagate = {}
        for ele in self.list_of_setting:
            if ele.split()[0] == 'PROPAGATE':
                all_propagate[ele.split()[1]] = Propagation(ele.split()[2],int(ele.split()[3]))
        return all_propagate

    def group_warning_info(self, warning_details):
        group = {}
        for detail in warning_details:
            type, device_receive, text, time = detail
            if text in group:
                group[text].append((type, device_receive, text, time))
            else:
                group[text] = [(type, device_receive, text,  time)]
        sorted_data = [sorted(group[text], key=lambda x: x[3]) for text in group]
        return sorted_data

    def read_warning_info(self):
        """The return dictionary shows in following format as [(type,device-sent-to,text,time)]
        for example as [('ALERT', '1', 'Trouble', '0')]"""
        warning_details = []
        for ele in self.list_of_setting:
            if ele.split()[0] == 'ALERT' or ele.split()[0] == 'CANCEL':
                warning_details.append(tuple(ele.split()))
        return self.group_warning_info(warning_details)


class Simulation:
    def __init__(self, device_list,simulation_time):
        self.written_file = []
        self.cancel_time = {}
        self.device_num = len(device_list)
        self.max_time = simulation_time
    def receive_message_cancel(self, current,before,text,time):
        self.written_file.append(f'@{time}: #{current} RECEIVED CANCELLATION FROM #{before}: {text}')

    def receive_message_alert(self, current,before,text,time):
        self.written_file.append(f'@{time}: #{current} RECEIVED ALERT FROM #{before}: {text}')

    def send_message_cancel(self, current,future,text,time):
        self.written_file.append(f'@{time}: #{current} SENT CANCELLATION TO #{future}: {text}')
        self.cancel_time[(current, text)] = time


    def send_message_alert(self, current,future,text,time):
        self.written_file.append(f'@{time}: #{current} SENT ALERT TO #{future}: {text}')



    def cancel_process(self,cancel_task,order):
        type, current_device, text, time = cancel_task[0], cancel_task[1],cancel_task[2],int(cancel_task[3])
        future_device = order[current_device].send_to
        if time < self.max_time:
            self.send_message_cancel(current_device, future_device, text, time)
            time += order[current_device].delay
        for i in range(1, self.device_num):
            if time < self.max_time:
                self.receive_message_cancel(future_device, current_device, text, time)
                current_device = future_device
                future_device = order[current_device].send_to
                self.send_message_cancel(current_device, future_device, text, time)
                time += order[current_device].delay
            else:
                break
        if time < self.max_time:
            self.receive_message_cancel(future_device, current_device, text, time)
            time += order[current_device].delay

    def alert_process(self, alert_task, order):
        type, current_device, text, time = alert_task[0], alert_task[1], alert_task[2], int(
            alert_task[3])
        future_device = order[current_device].send_to
        if (current_device, text) in self.cancel_time.keys() and time > self.cancel_time[(current_device, text)]:
            return
        if self.max_time > time:
            self.send_message_alert(current_device, future_device, text, time)
            time += order[current_device].delay
        while time < self.max_time:
            self.receive_message_alert(future_device, current_device, text, time)

            if (future_device, text) in self.cancel_time.keys() and time > self.cancel_time[(future_device, text)]:
                break
            else:
                current_device = future_device
                future_device = order[current_device].send_to
                self.send_message_alert(current_device, future_device, text, time)
                time += order[current_device].delay


    def simulation_process(self, sorted_warning_info,propagation_order):
        for ele in sorted_warning_info:
            if len(ele) == 1:
                if ele[0][0] == 'ALERT':
                    self.alert_process(ele[0],propagation_order)
                else:
                    self.cancel_process(ele[0],propagation_order)
            else:
                if ele[0][0] == 'ALERT':
                    self.cancel_process(ele[1], propagation_order)
                    self.alert_process(ele[0],propagation_order)
                else:
                    self.cancel_process(ele[0], propagation_order)
                    self.alert_process(ele[1], propagation_order)

    def sort_key(self, item):
        parts = item.split('@')
        time = int(parts[1].split(':')[0])
        return time

    def process_final_written_test(self):
        self.written_file = sorted(self.written_file, key = self.sort_key)
        self.written_file.append(f'@{self.max_time}: END')
        for line in self.written_file:
            print(line)



# All the functions inside the main() have been testified.
# It will take an address input and eventually print out each line.
def main() -> None:
    """Runs the simulation program in its entirety"""
    path = read_file_path()
    raw_data = read_all_info_in_file(path)
    data = Gather_Info_from_File(raw_data)
    simulation = Simulation(data.read_all_devices(), data.read_total_simulation_time())
    simulation.simulation_process(data.read_warning_info(),data.read_propagate_process())
    simulation.process_final_written_test()


if __name__ == '__main__':
    main()
