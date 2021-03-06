#!/usr/bin/env python3

from __future__ import print_function
import heapq
import pprint
import random
import sys

assert sys.version_info[0] >= 3

weekarrivals = 5000
reldayattends = [
    0.158055144,0.141951248,0.141242013,0.139010815,0.134600165,
    0.136450873,0.148717898
]
relhourattends = [
    0.021955416,0.017915919,0.014026032,0.012211999,
    0.01168836,0.010267056,0.012679533,0.018626571,
    0.034204817,0.054907241,0.059489078,0.065380012,
    0.06399611,0.063491173,0.06059246,0.06291143,
    0.064239228,0.06046155,0.064257929,0.060480251,
    0.054084381,0.044939408,0.037514961,0.029679084,
]

DOCTOR_ROTA = [
    ((0*60, 8*60-1), 11),
    ((8*60, 16*60-1), 15),
    ((16*60, 24*60-1), 6),
]
NUM_BLOODS = 2
NUM_XRAYS = 2
BLOOD_PROB = 0.2
XRAY_PROB = 0.1

def cmp(a, b):
    return (a > b) - (a < b)
# mixin class for Python3 supporting __cmp__
class PY3__cmp__:
    def __eq__(self, other):
        return self.__cmp__(other) == 0
    def __ne__(self, other):
        return self.__cmp__(other) != 0
    def __gt__(self, other):
        return self.__cmp__(other) > 0
    def __lt__(self, other):
        return self.__cmp__(other) < 0
    def __ge__(self, other):
        return self.__cmp__(other) >= 0
    def __le__(self, other):
        return self.__cmp__(other) <= 0

def gen_doctor_duration():
    return int(max(random.normalvariate(20, 20), 1))
def gen_blood_duration():
    if random.uniform(0, 1) > BLOOD_PROB:
        return None
    return int(max(random.normalvariate(20, 20), 10))
def gen_xray_duration():
    if random.uniform(0, 1) > XRAY_PROB:
        return None
    return int(max(random.normalvariate(20, 20), 20))

class Patient(PY3__cmp__):
    def __init__(self, priority, doctor_duration, blood_duration, xray_duration):
        assert 1 <= priority <= 5
        self.priority = priority
        self.doctor_duration = doctor_duration
        self.blood_duration = blood_duration
        self.xray_duration = xray_duration
        self.arrived = None
        self.started_doctor = None
        self.started_blood = None
        self.started_xray = None
        self.finished = None
    def __repr__(self):
        return 'Patient(priority={})'.format(self.priority)
    def __cmp__(self, other):
        return self.priority - other.priority
    def finished_with_doctor(self, minute):
        return minute - self.started_doctor == self.doctor_duration
    def finished_with_blood(self, minute):
        return minute - self.started_blood == self.blood_duration
    def finished_with_xray(self, minute):
        return minute - self.started_xray == self.xray_duration

class DoctorSlots:
    def __init__(self, slot_details):
        self.xx = []
        for (min_start, min_end), num_slots in slot_details:
            assert min_start < 24*60 and min_end < 24*60
            self.xx.append(((min_start, min_end), Slots(num_slots)))
    def have_free(self, minute):
        day_minute = minute % (24*60)
        for (min_start, min_end), slots in self.xx:
            if min_start <= day_minute <= min_end:
                return slots.have_free(minute)
        assert False
    def assign_patient(self, minute, patient):
        day_minute = minute % (24*60)
        for (min_start, min_end), slots in self.xx:
            if min_start <= day_minute <= min_end:
                return slots.assign_patient(minute, patient)
        assert False
    def done_patients(self, fn, minute):
        done_patients = []
        for _, slots in self.xx:
            done_patients.extend(slots.done_patients(fn, minute))
        return done_patients

class Slots:
    def __init__(self, total_num):
        self.__total_num = total_num
        self.current_patients = []
    def have_free(self, minute):
        return len(self.current_patients) < self.__total_num
    def assign_patient(self, minute, patient):
        self.current_patients.append(patient)
    def done_patients(self, fn, minute):
        new_current_patients = []
        done_patients = []
        for patient in self.current_patients:
            if fn(patient, minute):
                done_patients.append(patient)
            else:
                new_current_patients.append(patient)
        self.current_patients = new_current_patients
        return done_patients

PATIENT_ARRIVALS = []
def gen_patient_arrivals():
    for day in range(7):
        for hour in range(24):
            numarrivals = int(weekarrivals * reldayattends[day] * relhourattends[hour])
            for _ in range(numarrivals):
                arrivaltime = round((24*60*day) + (60*hour) + (random.uniform(0, 1)*59))
                PATIENT_ARRIVALS.append(arrivaltime)
    PATIENT_ARRIVALS.sort(reverse=True)

def patients_in_minute(minute):
    patients = []
    while PATIENT_ARRIVALS and PATIENT_ARRIVALS[-1] == minute:
        arrivaltime = PATIENT_ARRIVALS.pop()

        priority = random.randint(1, 5)
        doctor_duration = gen_doctor_duration()
        blood_duration = gen_blood_duration()
        xray_duration = gen_xray_duration()

        patient = Patient(priority, doctor_duration, blood_duration, xray_duration)
        patient.arrived = minute
        patients.append(patient)
    return patients

def transition_patient(minute, patient, doctor_queue, blood_queue, xray_queue, finished_patients):
    assert patient.doctor_duration is not None and patient.started_doctor is not None
    if patient.blood_duration and not patient.started_blood:
        blood_queue.append(patient)
        blood_queue.sort()
    elif patient.xray_duration and not patient.started_xray:
        xray_queue.append(patient)
        xray_queue.sort()
    else:
        patient.finished = minute
        finished_patients.append(patient)

def sim_minute(minute, doctor_queue, blood_queue, xray_queue, finished_patients, doctor_slots, blood_slots, xray_slots):
    doctor_queue.extend(patients_in_minute(minute))
    doctor_queue.sort()

    while doctor_slots.have_free(minute) and len(doctor_queue):
        patient = doctor_queue.pop()
        patient.started_doctor = minute
        doctor_slots.assign_patient(minute, patient)
    for patient in doctor_slots.done_patients(Patient.finished_with_doctor, minute):
        transition_patient(minute, patient, doctor_queue, blood_queue, xray_queue, finished_patients)

    while blood_slots.have_free(minute) and len(blood_queue):
        patient = blood_queue.pop()
        patient.started_blood = minute
        blood_slots.assign_patient(minute, patient)
    for patient in blood_slots.done_patients(Patient.finished_with_blood, minute):
        transition_patient(minute, patient, doctor_queue, blood_queue, xray_queue, finished_patients)

    while xray_slots.have_free(minute) and len(xray_queue):
        patient = xray_queue.pop()
        patient.started_xray = minute
        xray_slots.assign_patient(minute, patient)
    for patient in xray_slots.done_patients(Patient.finished_with_xray, minute):
        transition_patient(minute, patient, doctor_queue, xray_queue, xray_queue, finished_patients)

def readabletime(minute):
    assert minute % 60 == 0
    daynum = minute // (24*60)
    dayname = ['Mon', 'Tues', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun'][daynum]
    dayminute = minute % (24*60)
    dayhour = dayminute // 60
    return '{} {}00'.format(dayname, str(dayhour).zfill(2))

def go():
    gen_patient_arrivals()
    doctor_queue = []
    blood_queue = []
    xray_queue = []
    finished_patients = []
    doctor_slots = DoctorSlots(DOCTOR_ROTA)
    blood_slots = Slots(NUM_BLOODS)
    xray_slots = Slots(NUM_XRAYS)

    # TODO: add warmup - queue isn't empty at beginning of day
    for minute in range(0, 7*24*60):
        if minute % 60 == 0:
            print('At {}, DQ:{}, BQ:{}, XQ:{}, FIN:{}'.format(
                readabletime(minute),
                len(doctor_queue), len(blood_queue), len(xray_queue), len(finished_patients)
            ))
        sim_minute(minute, doctor_queue, blood_queue, xray_queue, finished_patients, doctor_slots, blood_slots, xray_slots)

    print('Saw {} patients'.format(len(finished_patients)))
    num_under_four_hours = 0
    num_over_four_hours = 0
    for patient in finished_patients:
        minutes = patient.finished - patient.arrived
        if minutes < 4*60:
            num_under_four_hours += 1
        else:
            num_over_four_hours += 1
    return (num_under_four_hours, num_over_four_hours)

def srv():
    import socket

    def dosim(data):
        num_rota1, num_rota2, num_rota3 = data.split(',')
        DOCTOR_ROTA[0] = (DOCTOR_ROTA[0][0], int(num_rota1))
        DOCTOR_ROTA[1] = (DOCTOR_ROTA[1][0], int(num_rota2))
        DOCTOR_ROTA[2] = (DOCTOR_ROTA[2][0], int(num_rota3))
        print(DOCTOR_ROTA)
        num_under_four_hours, num_over_four_hours = go()
        return '{},{}'.format(num_under_four_hours, num_over_four_hours)

    class Server:
        def __init__(self, host="127.0.0.1", port=8080):
            self.Sock = socket.socket()
            self.Sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.Host = host
            self.Port = port
            self.Sock.bind((self.Host, self.Port))

        def goLive(self, handshake, reaction):
            self.Sock.listen(10)
            while True:
                incomingConn, addr = self.Sock.accept()  # Establish connection with client.
                handshake(incomingConn, addr) # Code to run on connection
                data = incomingConn.recv(1080)
                print(type(data), data)
                if data != b'':
                    reaction(incomingConn, addr, data)  # code to run when a message comes in


    def handshake(incomingConn, addr):
        print('Got connection from', addr)
        incomingConn.send('Thank you for connecting'.encode())

    def reaction(incomingConn, addr, data):
        print("data.decode", data.decode('utf-8'))
        returnMessage = dosim(data.decode('utf-8'))
        incomingConn.send(returnMessage.encode('utf-8'))
        incomingConn.close()

    server = Server(host='0.0.0.0')
    server.goLive(
       handshake,
       reaction
    )

if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'srv':
        srv()
    else:
        try:
            go()
        except:
            import pdb, traceback
            type, value, tb = sys.exc_info()
            traceback.print_exc()
            pdb.post_mortem(tb)
