from time import time, sleep
from logging import (getLogger, StreamHandler, Formatter)
from argparse import ArgumentParser
from datetime import datetime
from epics import caput
from p4p.client.thread import Context
from matlab.engine import (start_matlab, InterruptedError)


# Establish logging
logger = getLogger()
handler = StreamHandler()
formatter = Formatter('[%(asctime)s] [%(levelname)-8s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel("WARNING")
handler.setLevel("WARNING")


# Ordered list of dict keys used by TWISS NTTable
TWISS_KEYS = ['p0c', 'psi_x', 'beta_x', 'alpha_x', 'eta_x', 'etap_x',
              'psi_y', 'beta_y', 'alpha_y', 'eta_y', 'etap_y']


def update_pv_value(pv, n, devices, z_pos, l_eff, r_mat=None, twiss=None):
    """Save data to the NTTable, starting with the common data for RMAT
    and TWISS PVs, then doing one or the other. Requires user to provide
    either r_mat or twiss data, but not both.

    Args:
        pv (NTTable): The data recieved from PVA and will be written to.
        n (list): The element names from MATLAB's model_rMatGet().
        devices (list): The device names for each element.
        z_pos (2-D list): The z-positions of elements.
        l_eff (2-D list): The effective lengths of elements.
        r_mat (3-D list): The transport matrices for elements.
        twiss (2-D list): The twiss parameters for elements.
    """
    if r_mat is None and twiss is None:
        raise ValueError("Provide one of the following r_mat or twiss")
    elif r_mat is not None and twiss is not None:
        raise ValueError("Provide either r_mat or twiss, but not both")

    pv['value']['element'] = n
    pv['value']['device_name'] = devices
    pv['value']['s'] = z_pos[0]
    pv['value']['z'] = z_pos[0]
    pv['value']['length'] = l_eff[0]

    if r_mat is not None:
        for i in range(6):
            for j in range(6):
                key = 'r' + str(i + 1) + str(j + 1)
                pv['value'][key] = r_mat[i][j]

    if twiss is not None:
        for ind, key in enumerate(TWISS_KEYS):
            pv['value'][key] = twiss[ind]


def periodic_pvs(pva, m_eng, element_devices_dict, b_path, p_type):
    """Update the RMAT & TWISS PVs for the given Beam Path and Model
    Type. This is done by running the MATLAB function model_rMatGet()
    and saving the data in associated PVs.

    Args:
        pva (Context): The PVAccess Context used to get/write PVA PVs.
        m_eng (MatlabEngine): The MATLAB Engine used to get data.
        element_devices_dict (dict): Dictionary containing element and
            device names.
        b_path (str): The Beam Path of the requested data.
        p_type (str): The Model Type of the requested data.
    """
    logger.info(f"{b_path}:{p_type}\tStart")

    get_type = "EXTANT" if p_type == "LIVE" else "DESIGN"

    # Run the MATLAB function model_rMatGet() (the energy variable is unused)
    r_mat, z_pos, l_eff, twiss, _, n = m_eng.model_rMatGet(
        b_path,
        [],
        [f'BEAMPATH={b_path}', f'TYPE={get_type}'],
        nargout=6
    )

    devices = [element_devices_dict.get(ele, ele) for ele in n]

    # Save RMAT data; TypeError thrown if data includes complex numbers
    try:
        r_mat_pv = pva.get(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT")
        update_pv_value(r_mat_pv, n, devices, z_pos, l_eff, r_mat=r_mat)

        proc_time = datetime.now().isoformat(sep=' ', timespec="seconds")
        pva.put(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT", r_mat_pv)
        caput(f"BLEM:SYS0:1:{b_path}:{p_type}:RMAT_TOD", proc_time)
    except TypeError as e:
        logger.error(f"{b_path}:{p_type}:RMAT\t{e.args[0]}")

    # Save TWISS data; TypeError thrown if data includes complex numbers
    try:
        twiss_pv = pva.get(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS")
        update_pv_value(twiss_pv, n, devices, z_pos, l_eff, twiss=twiss)

        proc_time = datetime.now().isoformat(sep=' ', timespec="seconds")
        pva.put(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS", twiss_pv)
        caput(f"BLEM:SYS0:1:{b_path}:{p_type}:TWISS_TOD", proc_time)
    except TypeError as e:
        logger.error(f"{b_path}:{p_type}:TWISS\t{e.args[0]}")

    logger.info(f"{b_path}:{p_type}\tEnd")


def get_element_dict(m_eng):
    """Create a dictionary where key = an element name used by the model
    data, and value = a device name to be saved to the PV.
    """
    # Get list of all element names (ignore non-str & duplicates)
    element_set = set()
    for e in m_eng.model_nameConvert('*', 'MAD'):
        if type(e) is str:
            element_set.add(e)
    elements = list(element_set)

    # Get a device name for each element name (non-str -> '')
    devices = []
    for d in m_eng.model_nameConvert(elements):
        if type(d) is str:
            devices.append(d)
        else:
            devices.append('')

    return dict(zip(elements, devices))


def main():
    """For the given Beam Path and Model Type, open a MATLAB engine and
    repeatedly (<= 1Hz) populate the associated PV with model data.
    """
    # Parse arguments passed into the program
    parser = ArgumentParser(prog="BLEM PV Service")
    parser.add_argument("b_path", metavar="Beam Path")
    parser.add_argument("p_type", choices=['LIVE', 'DESIGN'])
    args = parser.parse_args()

    # Open a PVAccess connection with p4p
    pva = Context('pva', nt=False)

    # Start a MATLAB engine
    m_eng = start_matlab()

    # Populate a dictionary of {element name (str): device name (str)}
    element_devices_dict = get_element_dict(m_eng)

    # Populate associated PV continuously; at most once per second
    try:
        while True:
            start_time = time()
            periodic_pvs(pva, m_eng, element_devices_dict, args.b_path, args.p_type)
            elapsed_time = time() - start_time

            if elapsed_time < 1:
                sleep(1 - elapsed_time)
    except (KeyboardInterrupt, InterruptedError):
        logger.info("Closing connections")
    finally:
        pva.close()


if __name__ == "__main__":
    main()
