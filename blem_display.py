from os import getenv
from requests import get
from datetime import datetime
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QHeaderView
from pydm import Display


class BLEMDisplay(Display):
    def __init__(self, parent=None, args=None, macros=None, ui_filename=None):
        super().__init__(parent=parent, args=args, macros=macros,
                         ui_filename=__file__.replace(".py", ".ui"))

        self.archiver_url = getenv("PYDM_ARCHIVER_URL")
        self.archiver_url += "/retrieval/data/getData.json"

        nt_tbl = self.ui.model_pv_tbl._table
        hdr = nt_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)

        hdr = self.ui.archiver_tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.ui.path_cmbx.currentIndexChanged.connect(self.set_channels)
        self.ui.type_cmbx.currentIndexChanged.connect(self.set_channels)
        self.ui.model_cmbx.currentIndexChanged.connect(self.set_channels)
        self.ui.archiver_dt.send_value_signal.connect(self.update_archiver)

        self.set_channels()

    def is_design_pv(self):
        return self.ui.type_cmbx.currentText() == "DESIGN"

    def get_pv(self):
        b_path = self.ui.path_cmbx.currentText()
        p_type = self.ui.type_cmbx.currentText()
        model = self.ui.model_cmbx.currentText()

        return f"BLEM:SYS0:1:{b_path}:{p_type}:{model}"

    # @Slot(QDateTime)
    def update_archiver(self, get_dt):
        if self.is_design_pv():
            self.ui.warning_lbl.show()
            return
        self.ui.warning_lbl.hide()

        archived_pv = self.get_pv()

        arch_dt = datetime.utcfromtimestamp(get_dt)
        arch_dt_str = arch_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        payload = get(self.archiver_url,
                      params={"pv": archived_pv,
                              "from": arch_dt_str,
                              "to": arch_dt_str})

        data = payload.json()

    @Slot(int)
    def set_channels(self, **kw):
        model_pv = self.get_pv()
        base = model_pv.rsplit(':', maxsplit=1)[0]

        self.ui.model_cnt_lbl.channel = f"ca://{model_pv}_CNT"
        self.ui.model_tod_lbl.channel = f"ca://{model_pv}_TOD"
        self.ui.stat_lbl.channel = f"ca://{base}:STAT"
        self.ui.err_cnt_lbl.channel = f"ca://{base}:ERR_CNT"

        self.ui.model_pv_tbl.channel = f"pva://{model_pv}"
