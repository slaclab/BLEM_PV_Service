from io import StringIO
from logging import (getLogger, StreamHandler, Formatter)
from argparse import ArgumentParser
from datetime import datetime
from epics import (caput, PV)
from p4p.client.thread import Context
from matlab.engine import start_matlab


# Establish logging
logger = getLogger()
handler = StreamHandler()
formatter = Formatter('[%(asctime)s] [%(levelname)-8s] - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel("WARNING")
handler.setLevel("WARNING")


# Capture MATLAB's stdout & stderr
nullout = StringIO()


# Ordered list of dict keys used by TWISS NTTable
TWISS_KEYS = ['p0c', 'psi_x', 'beta_x', 'alpha_x', 'eta_x', 'etap_x',
              'psi_y', 'beta_y', 'alpha_y', 'eta_y', 'etap_y']
# Rate PV for each destination
RATE_PV_MAP = {'CU_HXR': "IOC:BSY0:MP01:BYKIK_RATE",
               'CU_SXR': "IOC:BSY0:MP01:BYKIKS_RATE",
               'SC_DIAG0': "TPG:SYS0:1:DST01:RATE",
               'SC_BSYD': "TPG:SYS0:1:DST02:RATE",
               'SC_HXR': "TPG:SYS0:1:DST03:RATE",
               'SC_SXR': "TPG:SYS0:1:DST04:RATE"}
PV_PREFIX = None


def write_status(msg, err=False):
    """Write a message to stdout with the logger and write it to a
    status PV.

    Args:
        msg (str): The status message to write.
        err (bool): Determines the logging level.
    """
    if not err:
        status_msg = f"[INFO] - {msg}"
    else:
        logger.error(msg)
        status_msg = f"[ERROR] - {msg}"

    if len(status_msg) > 40:
        status_msg = status_msg[:36] + "..."
    caput(f"{PV_PREFIX}:STAT", status_msg)


def running_beam(b_path):
    """A quick preliminary check to determine if beam is running to the
    requested area."""
    rate_pv = PV(RATE_PV_MAP[b_path], verbose=False)
    if not rate_pv.wait_for_connection():
        return False
    value = rate_pv.value

    if b_path[:2] == "CU":
        try:
            state_str = rate_pv.enum_strs[value]
            value = int(state_str.split()[0])
        except (ValueError, IndexError, AttributeError):
            # This except accounts for an invalid string or type
            return False

    return value > 0


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


def populate_pvs(pva, m_eng, element_devices_dict, b_path, p_type):
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
    # Run the MATLAB function model_rMatGet() (the energy variable is unused)
    get_type = "EXTANT" if p_type == "LIVE" else "DESIGN"
    r_mat, z_pos, l_eff, twiss, _, n = m_eng.model_rMatGet(
        b_path,
        [],
        [f'BEAMPATH={b_path}', f'TYPE={get_type}'],
        nargout=6,
        stdout=nullout,
        stderr=nullout
    )

    devices = [element_devices_dict.get(ele, ele) for ele in n]

    # Save RMAT data; TypeError thrown if data includes complex numbers
    try:
        r_mat_pv = pva.get(f"{PV_PREFIX}:RMAT")
        update_pv_value(r_mat_pv, n, devices, z_pos, l_eff, r_mat=r_mat)

        proc_time = datetime.now().isoformat(sep=' ', timespec="seconds")
        pva.put(f"{PV_PREFIX}:RMAT", r_mat_pv)
        caput(f"{PV_PREFIX}:RMAT_TOD", proc_time)

        counter = PV(f"{PV_PREFIX}:RMAT_CNT", verbose=False)
        counter.value += 1
    except (TypeError, TimeoutError) as e:
        write_status(f"RMAT {str(e)}", err=True)

    # Save TWISS data; TypeError thrown if data includes complex numbers
    try:
        twiss_pv = pva.get(f"{PV_PREFIX}:TWISS")
        update_pv_value(twiss_pv, n, devices, z_pos, l_eff, twiss=twiss)

        proc_time = datetime.now().isoformat(sep=' ', timespec="seconds")
        pva.put(f"{PV_PREFIX}:TWISS", twiss_pv)
        caput(f"{PV_PREFIX}:TWISS_TOD", proc_time)

        counter = PV(f"{PV_PREFIX}:TWISS_CNT", verbose=False)
        counter.value += 1
    except (TypeError, TimeoutError) as e:
        write_status(f"TWISS {str(e)}", err=True)


def get_element_dict(m_eng):
    """Create a dictionary where key = an element name used by the model
    data, and value = a device name to be saved to the PV.
    """
    # Get list of all element names (ignore non-str & duplicates)
    element_set = set()
    for e in m_eng.model_nameConvert('*', 'MAD', stdout=nullout, stderr=nullout):
        if type(e) is str:
            element_set.add(e)
    elements = list(element_set)

    # Get a device name for each element name (non-str -> '')
    devices = []
    for d in m_eng.model_nameConvert(elements, stdout=nullout, stderr=nullout):
        if type(d) is str:
            devices.append(d)
        else:
            devices.append('')

    return dict(zip(elements, devices))


def main():
    """For the given Beam Path and Model Type, open a MATLAB engine and
    the associated PV with model data.
    """
    valid_paths = ["CU_HXR", "CU_SXR", "SC_HXR", "SC_SXR", "SC_DIAG0", "SC_BSYD"]
    # Parse arguments passed into the program
    parser = ArgumentParser(prog="BLEM PV Service")
    parser.add_argument("b_path", metavar="Beam Path", choices=valid_paths)
    parser.add_argument("p_type", choices=['LIVE', 'DESIGN'])
    args = parser.parse_args()

    if not running_beam(args.b_path):
        return

    global PV_PREFIX
    PV_PREFIX = f"BLEM:SYS0:1:{args.b_path}:{args.p_type}"

    write_status("Running script")

    # Open a PVAccess connection with p4p
    pva = Context('pva', nt=False)

    # Start a MATLAB engine
    m_eng = start_matlab()

    # Populate a dictionary of {element name (str): device name (str)}
    element_devices_dict = get_element_dict(m_eng)

    # Populate associated PV
    populate_pvs(pva, m_eng, element_devices_dict, args.b_path, args.p_type)

    write_status("Ending script")
    pva.close()
    m_eng.quit()


if __name__ == "__main__":
    main()
