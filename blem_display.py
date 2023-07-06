from qtpy.QtCore import Slot
from qtpy.QtWidgets import QHeaderView
from pydm import Display


class BLEMDisplay(Display):
    def __init__(self, parent=None, args=None, macros=None, ui_filename=None):
        super().__init__(parent=parent, args=args, macros=macros,
                         ui_filename=__file__.replace(".py", ".ui"))

        nt_tbl = self.ui.model_pv_tbl._table
        hdr = nt_tbl.horizontalHeader()
        hdr.setResizeMode(QHeaderView.ResizeToContents)

        self.ui.path_cmbx.currentIndexChanged.connect(self.set_channels)
        self.ui.type_cmbx.currentIndexChanged.connect(self.set_channels)
        self.ui.model_cmbx.currentIndexChanged.connect(self.set_channels)

        self.set_channels()

    def get_pv(self):
        b_path = self.ui.path_cmbx.currentText()
        p_type = self.ui.type_cmbx.currentText()
        model = self.ui.model_cmbx.currentText()

        return f"BLEM:SYS0:1:{b_path}:{p_type}:{model}"

    @Slot(int)
    def set_channels(self, **kw):
        model_pv = self.get_pv()
        base = model_pv.rsplit(':', maxsplit=1)[0]

        self.ui.model_cnt_lbl.channel = f"ca://{model_pv}_CNT"
        self.ui.model_tod_lbl.channel = f"ca://{model_pv}_TOD"
        self.ui.stat_lbl.channel = f"ca://{base}:STAT"
        self.ui.err_cnt_lbl.channel = f"ca://{base}:ERR_CNT"

        self.ui.model_pv_tbl.channel = f"pva://{model_pv}"
