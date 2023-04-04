from time import time, sleep
from logging import getLogger, StreamHandler, Formatter
from argparse import ArgumentParser
from datetime import datetime
from epics import caput
from p4p.client.thread import Context
from matlab.engine import start_matlab


logger = getLogger()
handler = StreamHandler()
formatter = Formatter('[%(asctime)s] [%(levelname)-8s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel("WARNING")
handler.setLevel("WARNING")


TWISS_KEYS = {'p0c': 0,
              'psi_x': 1,
              'beta_x': 2,
              'alpha_x': 3,
              'eta_x': 4,
              'etap_x': 5,
              'psi_y': 6,
              'beta_y': 7,
              'alpha_y': 8,
              'eta_y': 9,
              'etap_y': 10}


def periodic_pvs(pva, m_eng, element_devices_dict, b_path, p_type):
    logger.info(f"{b_path}:{p_type}\tStart")

    get_type = "EXTANT" if p_type == "LIVE" else "DESIGN"

    # Run the Matlab function model_rMatGet() (the energy variable is unused)
    r_mat, z_pos, l_eff, twiss, _, n = m_eng.model_rMatGet(
        b_path,
        [],
        [f'BEAMPATH={b_path}', f'TYPE={get_type}'],
        nargout=6
    )

    devices = [element_devices_dict.get(ele, ele) for ele in n]

    r_mat_pv = pva.get(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT")
    r_mat_pv['value']['element'] = n
    r_mat_pv['value']['device_name'] = devices
    r_mat_pv['value']['s'] = z_pos[0]
    r_mat_pv['value']['z'] = z_pos[0]
    r_mat_pv['value']['length'] = l_eff[0]
    for i in range(6):
        for j in range(6):
            key = 'r' + str(i + 1) + str(j + 1)
            r_mat_pv['value'][key] = r_mat[i][j]

    twiss_pv = pva.get(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS")
    twiss_pv['value']['element'] = n
    twiss_pv['value']['device_name'] = devices
    twiss_pv['value']['s'] = z_pos[0]
    twiss_pv['value']['z'] = z_pos[0]
    twiss_pv['value']['length'] = l_eff[0]
    for key, ind in TWISS_KEYS.items():
        twiss_pv['value'][key] = twiss[ind]

    pva.put(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT", r_mat_pv)
    pva.put(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS", twiss_pv)

    proc_time = datetime.now().isoformat(sep=' ', timespec="seconds")
    caput(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT_TOD", proc_time)
    caput(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS_TOD", proc_time)

    logger.info(f"{b_path}:{p_type}\tEnd")


def get_element_dict(m_eng):
    element_set = set()
    for e in m_eng.model_nameConvert('*', 'MAD'):
        if type(e) is str:
            element_set.add(e)
    elements = list(element_set)

    devices = []
    for d in m_eng.model_nameConvert(elements):
        if type(d) is str:
            devices.append(d)
        else:
            devices.append('')

    return dict(zip(elements, devices))


def main():
    parser = ArgumentParser(prog="BLEM PV Service")
    parser.add_argument("b_path", metavar="Beam Path")
    parser.add_argument("p_type", choices=['LIVE', 'DESIGN'])
    args = parser.parse_args()

    pva = Context('pva', nt=False)

    m_eng = start_matlab()
    element_devices_dict = get_element_dict(m_eng)

    try:
        while True:
            start_time = time()

            if args.p_type in ["LIVE", "DESIGN"]:
                periodic_pvs(pva, m_eng, element_devices_dict, args.b_path, args.p_type)

            elapsed_time = time() - start_time

            if elapsed_time < 1:
                sleep(1 - elapsed_time)
    except KeyboardInterrupt:
        logger.info("Closing connections")
    finally:
        pva.close()


if __name__ == "__main__":
    main()
