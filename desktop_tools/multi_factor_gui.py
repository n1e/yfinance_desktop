from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QMessageBox, QProgressBar, QTabWidget, QFormLayout, QDialog,
    QLineEdit, QDialogButtonBox, QSlider
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from typing import List, Dict, Any, Optional
from datetime import datetime

from .watchlist import WatchlistManager
from .config import ConfigManager
from .multi_factor_screener import (
    MultiFactorScreener, StrategyConfig, FactorConfig,
    FactorType, LogicOperator, StockAnalysisResult, FactorResult
)


class FactorConfigWidget(QWidget):
    def __init__(self, factor_type: str, parent=None):
        super().__init__(parent)
        self._factor_type = factor_type
        self._factor_config: Optional[FactorConfig] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        header_layout = QHBoxLayout()
        self._enable_check = QCheckBox(self._get_factor_name())
        self._enable_check.setChecked(False)
        self._enable_check.stateChanged.connect(self._on_enabled_changed)
        header_layout.addWidget(self._enable_check)

        header_layout.addStretch()

        weight_layout = QHBoxLayout()
        weight_layout.addWidget(QLabel("权重:"))
        self._weight_spin = QSpinBox()
        self._weight_spin.setRange(0, 100)
        self._weight_spin.setValue(20)
        self._weight_spin.setSuffix(" 分")
        self._weight_spin.setEnabled(False)
        weight_layout.addWidget(self._weight_spin)
        header_layout.addLayout(weight_layout)

        layout.addLayout(header_layout)

        self._param_widget = QWidget()
        param_layout = QVBoxLayout(self._param_widget)
        param_layout.setContentsMargins(20, 5, 5, 5)
        self._create_param_widgets(param_layout)
        self._param_widget.setEnabled(False)
        layout.addWidget(self._param_widget)

    def _get_factor_name(self) -> str:
        names = {
            'MA': "MA均线",
            'RSI': "RSI相对强弱指标",
            'MACD': "MACD指标",
            'BOLLINGER': "布林带",
            'KDJ': "KDJ指标",
            'PE': "PE估值"
        }
        return names.get(self._factor_type, self._factor_type)

    def _create_param_widgets(self, layout: QVBoxLayout):
        if self._factor_type == 'MA':
            self._create_ma_params(layout)
        elif self._factor_type == 'RSI':
            self._create_rsi_params(layout)
        elif self._factor_type == 'MACD':
            self._create_macd_params(layout)
        elif self._factor_type == 'BOLLINGER':
            self._create_bollinger_params(layout)
        elif self._factor_type == 'KDJ':
            self._create_kdj_params(layout)
        elif self._factor_type == 'PE':
            self._create_pe_params(layout)

    def _create_ma_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        short_layout = QHBoxLayout()
        self._ma_short_spin = QSpinBox()
        self._ma_short_spin.setRange(2, 200)
        self._ma_short_spin.setValue(5)
        self._ma_short_spin.setSuffix(" 周期")
        short_layout.addWidget(self._ma_short_spin)
        short_layout.addStretch()
        form_layout.addRow("短期均线周期:", short_layout)

        long_layout = QHBoxLayout()
        self._ma_long_spin = QSpinBox()
        self._ma_long_spin.setRange(5, 500)
        self._ma_long_spin.setValue(20)
        self._ma_long_spin.setSuffix(" 周期")
        long_layout.addWidget(self._ma_long_spin)
        long_layout.addStretch()
        form_layout.addRow("长期均线周期:", long_layout)

        condition_layout = QHBoxLayout()
        self._ma_condition_combo = QComboBox()
        self._ma_condition_combo.addItems([
            "金叉/死叉",
            "价格高于长期均线",
            "均线向上"
        ])
        condition_layout.addWidget(self._ma_condition_combo)
        condition_layout.addStretch()
        form_layout.addRow("判断条件:", condition_layout)

        layout.addLayout(form_layout)

    def _create_rsi_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        period_layout = QHBoxLayout()
        self._rsi_period_spin = QSpinBox()
        self._rsi_period_spin.setRange(5, 30)
        self._rsi_period_spin.setValue(14)
        self._rsi_period_spin.setSuffix(" 周期")
        period_layout.addWidget(self._rsi_period_spin)
        period_layout.addStretch()
        form_layout.addRow("RSI周期:", period_layout)

        oversold_layout = QHBoxLayout()
        self._rsi_oversold_spin = QSpinBox()
        self._rsi_oversold_spin.setRange(10, 40)
        self._rsi_oversold_spin.setValue(30)
        self._rsi_oversold_spin.setSuffix("")
        oversold_layout.addWidget(self._rsi_oversold_spin)
        oversold_layout.addStretch()
        form_layout.addRow("超卖阈值:", oversold_layout)

        overbought_layout = QHBoxLayout()
        self._rsi_overbought_spin = QSpinBox()
        self._rsi_overbought_spin.setRange(60, 90)
        self._rsi_overbought_spin.setValue(70)
        self._rsi_overbought_spin.setSuffix("")
        overbought_layout.addWidget(self._rsi_overbought_spin)
        overbought_layout.addStretch()
        form_layout.addRow("超买阈值:", overbought_layout)

        layout.addLayout(form_layout)

    def _create_macd_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        fast_layout = QHBoxLayout()
        self._macd_fast_spin = QSpinBox()
        self._macd_fast_spin.setRange(5, 50)
        self._macd_fast_spin.setValue(12)
        self._macd_fast_spin.setSuffix(" 周期")
        fast_layout.addWidget(self._macd_fast_spin)
        fast_layout.addStretch()
        form_layout.addRow("快线周期:", fast_layout)

        slow_layout = QHBoxLayout()
        self._macd_slow_spin = QSpinBox()
        self._macd_slow_spin.setRange(10, 100)
        self._macd_slow_spin.setValue(26)
        self._macd_slow_spin.setSuffix(" 周期")
        slow_layout.addWidget(self._macd_slow_spin)
        slow_layout.addStretch()
        form_layout.addRow("慢线周期:", slow_layout)

        signal_layout = QHBoxLayout()
        self._macd_signal_spin = QSpinBox()
        self._macd_signal_spin.setRange(3, 20)
        self._macd_signal_spin.setValue(9)
        self._macd_signal_spin.setSuffix(" 周期")
        signal_layout.addWidget(self._macd_signal_spin)
        signal_layout.addStretch()
        form_layout.addRow("信号线周期:", signal_layout)

        layout.addLayout(form_layout)

    def _create_bollinger_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        period_layout = QHBoxLayout()
        self._bollinger_period_spin = QSpinBox()
        self._bollinger_period_spin.setRange(10, 100)
        self._bollinger_period_spin.setValue(20)
        self._bollinger_period_spin.setSuffix(" 周期")
        period_layout.addWidget(self._bollinger_period_spin)
        period_layout.addStretch()
        form_layout.addRow("周期:", period_layout)

        std_layout = QHBoxLayout()
        self._bollinger_std_spin = QDoubleSpinBox()
        self._bollinger_std_spin.setRange(1.0, 3.0)
        self._bollinger_std_spin.setValue(2.0)
        self._bollinger_std_spin.setSingleStep(0.5)
        self._bollinger_std_spin.setSuffix(" 倍标准差")
        std_layout.addWidget(self._bollinger_std_spin)
        std_layout.addStretch()
        form_layout.addRow("标准差倍数:", std_layout)

        width_layout = QHBoxLayout()
        self._bollinger_width_spin = QDoubleSpinBox()
        self._bollinger_width_spin.setRange(1.0, 50.0)
        self._bollinger_width_spin.setValue(10.0)
        self._bollinger_width_spin.setSuffix("%")
        width_layout.addWidget(self._bollinger_width_spin)
        width_layout.addStretch()
        form_layout.addRow("宽度收窄阈值:", width_layout)

        layout.addLayout(form_layout)

    def _create_kdj_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        n_layout = QHBoxLayout()
        self._kdj_n_spin = QSpinBox()
        self._kdj_n_spin.setRange(5, 30)
        self._kdj_n_spin.setValue(9)
        self._kdj_n_spin.setSuffix(" 周期")
        n_layout.addWidget(self._kdj_n_spin)
        n_layout.addStretch()
        form_layout.addRow("N周期:", n_layout)

        m1_layout = QHBoxLayout()
        self._kdj_m1_spin = QSpinBox()
        self._kdj_m1_spin.setRange(1, 10)
        self._kdj_m1_spin.setValue(3)
        self._kdj_m1_spin.setSuffix(" 周期")
        m1_layout.addWidget(self._kdj_m1_spin)
        m1_layout.addStretch()
        form_layout.addRow("M1周期:", m1_layout)

        m2_layout = QHBoxLayout()
        self._kdj_m2_spin = QSpinBox()
        self._kdj_m2_spin.setRange(1, 10)
        self._kdj_m2_spin.setValue(3)
        self._kdj_m2_spin.setSuffix(" 周期")
        m2_layout.addWidget(self._kdj_m2_spin)
        m2_layout.addStretch()
        form_layout.addRow("M2周期:", m2_layout)

        layout.addLayout(form_layout)

    def _create_pe_params(self, layout: QVBoxLayout):
        form_layout = QFormLayout()

        min_layout = QHBoxLayout()
        self._pe_min_spin = QDoubleSpinBox()
        self._pe_min_spin.setRange(0.0, 100.0)
        self._pe_min_spin.setValue(5.0)
        self._pe_min_spin.setSingleStep(1.0)
        min_layout.addWidget(self._pe_min_spin)
        min_layout.addStretch()
        form_layout.addRow("最低PE:", min_layout)

        max_layout = QHBoxLayout()
        self._pe_max_spin = QDoubleSpinBox()
        self._pe_max_spin.setRange(1.0, 500.0)
        self._pe_max_spin.setValue(25.0)
        self._pe_max_spin.setSingleStep(1.0)
        max_layout.addWidget(self._pe_max_spin)
        max_layout.addStretch()
        form_layout.addRow("最高PE:", max_layout)

        layout.addLayout(form_layout)

    def _on_enabled_changed(self, state):
        enabled = state == Qt.Checked
        self._param_widget.setEnabled(enabled)
        self._weight_spin.setEnabled(enabled)

    def get_factor_config(self) -> FactorConfig:
        params = {}
        enabled = self._enable_check.isChecked()
        weight = self._weight_spin.value()

        if self._factor_type == 'MA':
            condition_map = {
                0: 'golden_cross',
                1: 'above_ma',
                2: 'ma_up'
            }
            params = {
                'ma_short': self._ma_short_spin.value(),
                'ma_long': self._ma_long_spin.value(),
                'condition': condition_map.get(self._ma_condition_combo.currentIndex(), 'golden_cross')
            }
        elif self._factor_type == 'RSI':
            params = {
                'period': self._rsi_period_spin.value(),
                'oversold': self._rsi_oversold_spin.value(),
                'overbought': self._rsi_overbought_spin.value()
            }
        elif self._factor_type == 'MACD':
            params = {
                'fast': self._macd_fast_spin.value(),
                'slow': self._macd_slow_spin.value(),
                'signal': self._macd_signal_spin.value()
            }
        elif self._factor_type == 'BOLLINGER':
            params = {
                'period': self._bollinger_period_spin.value(),
                'std_dev': self._bollinger_std_spin.value(),
                'width_threshold': self._bollinger_width_spin.value()
            }
        elif self._factor_type == 'KDJ':
            params = {
                'n': self._kdj_n_spin.value(),
                'm1': self._kdj_m1_spin.value(),
                'm2': self._kdj_m2_spin.value()
            }
        elif self._factor_type == 'PE':
            params = {
                'min_pe': self._pe_min_spin.value(),
                'max_pe': self._pe_max_spin.value()
            }

        return FactorConfig(
            factor_type=self._factor_type,
            enabled=enabled,
            weight=weight,
            params=params
        )

    def set_factor_config(self, config: FactorConfig):
        self._factor_config = config
        self._enable_check.setChecked(config.enabled)
        self._weight_spin.setValue(config.weight)
        params = config.params

        if self._factor_type == 'MA':
            self._ma_short_spin.setValue(params.get('ma_short', 5))
            self._ma_long_spin.setValue(params.get('ma_long', 20))
            condition_map = {
                'golden_cross': 0,
                'above_ma': 1,
                'ma_up': 2
            }
            self._ma_condition_combo.setCurrentIndex(
                condition_map.get(params.get('condition', 'golden_cross'), 0)
            )
        elif self._factor_type == 'RSI':
            self._rsi_period_spin.setValue(params.get('period', 14))
            self._rsi_oversold_spin.setValue(params.get('oversold', 30))
            self._rsi_overbought_spin.setValue(params.get('overbought', 70))
        elif self._factor_type == 'MACD':
            self._macd_fast_spin.setValue(params.get('fast', 12))
            self._macd_slow_spin.setValue(params.get('slow', 26))
            self._macd_signal_spin.setValue(params.get('signal', 9))
        elif self._factor_type == 'BOLLINGER':
            self._bollinger_period_spin.setValue(params.get('period', 20))
            self._bollinger_std_spin.setValue(params.get('std_dev', 2.0))
            self._bollinger_width_spin.setValue(params.get('width_threshold', 10.0))
        elif self._factor_type == 'KDJ':
            self._kdj_n_spin.setValue(params.get('n', 9))
            self._kdj_m1_spin.setValue(params.get('m1', 3))
            self._kdj_m2_spin.setValue(params.get('m2', 3))
        elif self._factor_type == 'PE':
            self._pe_min_spin.setValue(params.get('min_pe', 5.0))
            self._pe_max_spin.setValue(params.get('max_pe', 25.0))

    def is_enabled(self) -> bool:
        return self._enable_check.isChecked()


class StrategyNameDialog(QDialog):
    def __init__(self, existing_names: List[str], parent=None, default_name: str = ""):
        super().__init__(parent)
        self._existing_names = existing_names
        self._init_ui(default_name)

    def _init_ui(self, default_name: str):
        self.setWindowTitle("策略名称")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self._name_input = QLineEdit()
        self._name_input.setText(default_name)
        self._name_input.setPlaceholderText("请输入策略名称")
        form_layout.addRow("策略名称:", self._name_input)
        layout.addLayout(form_layout)

        self._message_label = QLabel("")
        self._message_label.setStyleSheet("color: red;")
        layout.addWidget(self._message_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_accept(self):
        name = self._name_input.text().strip()
        if not name:
            self._message_label.setText("请输入策略名称")
            return
        if name in self._existing_names:
            self._message_label.setText("该名称已存在")
            return
        self.accept()

    def get_name(self) -> str:
        return self._name_input.text().strip()


class AnalysisThread(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(
        self,
        screener: MultiFactorScreener,
        symbols: List[str],
        strategy: StrategyConfig,
        parent=None
    ):
        super().__init__(parent)
        self._screener = screener
        self._symbols = symbols
        self._strategy = strategy

    def run(self):
        try:
            def progress_callback(current: int, total: int, symbol: str):
                self.progress_signal.emit(current, total, symbol)

            results = self._screener.analyze_watchlist(
                self._symbols, self._strategy, progress_callback
            )
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))


class MultiFactorScreenerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._screener = MultiFactorScreener()
        self._watchlist_manager = WatchlistManager()
        self._config = ConfigManager()
        self._current_strategy: Optional[StrategyConfig] = None
        self._analysis_thread: Optional[AnalysisThread] = None
        self._factor_widgets: Dict[str, FactorConfigWidget] = {}
        self._current_results: List[StockAnalysisResult] = []
        self._init_ui()
        self._load_strategies()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        strategy_group = QGroupBox("策略管理")
        strategy_layout = QHBoxLayout(strategy_group)

        strategy_layout.addWidget(QLabel("当前策略:"))
        self._strategy_combo = QComboBox()
        self._strategy_combo.setMinimumWidth(200)
        self._strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self._strategy_combo)

        self._new_strategy_btn = QPushButton("新建策略")
        self._new_strategy_btn.clicked.connect(self._on_new_strategy)
        strategy_layout.addWidget(self._new_strategy_btn)

        self._save_strategy_btn = QPushButton("保存策略")
        self._save_strategy_btn.clicked.connect(self._on_save_strategy)
        strategy_layout.addWidget(self._save_strategy_btn)

        self._duplicate_strategy_btn = QPushButton("复制策略")
        self._duplicate_strategy_btn.clicked.connect(self._on_duplicate_strategy)
        strategy_layout.addWidget(self._duplicate_strategy_btn)

        self._delete_strategy_btn = QPushButton("删除策略")
        self._delete_strategy_btn.clicked.connect(self._on_delete_strategy)
        strategy_layout.addWidget(self._delete_strategy_btn)

        strategy_layout.addStretch()
        layout.addWidget(strategy_group)

        main_splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        logic_group = QGroupBox("交易逻辑设置")
        logic_layout = QHBoxLayout(logic_group)

        logic_layout.addWidget(QLabel("买入条件:"))
        self._buy_logic_combo = QComboBox()
        self._buy_logic_combo.addItems(["全部满足 (AND)", "满足任一 (OR)"])
        logic_layout.addWidget(self._buy_logic_combo)

        logic_layout.addSpacing(30)

        logic_layout.addWidget(QLabel("卖出条件:"))
        self._sell_logic_combo = QComboBox()
        self._sell_logic_combo.addItems(["全部满足 (AND)", "满足任一 (OR)"])
        logic_layout.addWidget(self._sell_logic_combo)

        logic_layout.addStretch()
        left_layout.addWidget(logic_group)

        factor_group = QGroupBox("因子配置")
        factor_layout = QVBoxLayout(factor_group)
        factor_layout.setSpacing(5)

        self._factor_widgets['MA'] = FactorConfigWidget('MA')
        self._factor_widgets['RSI'] = FactorConfigWidget('RSI')
        self._factor_widgets['MACD'] = FactorConfigWidget('MACD')
        self._factor_widgets['BOLLINGER'] = FactorConfigWidget('BOLLINGER')
        self._factor_widgets['KDJ'] = FactorConfigWidget('KDJ')
        self._factor_widgets['PE'] = FactorConfigWidget('PE')

        for widget in self._factor_widgets.values():
            factor_layout.addWidget(widget)

        factor_layout.addStretch()
        left_layout.addWidget(factor_group, 1)

        main_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        control_group = QGroupBox("分析控制")
        control_layout = QHBoxLayout(control_group)

        self._analyze_btn = QPushButton("分析所有自选股")
        self._analyze_btn.setMinimumHeight(40)
        self._analyze_btn.clicked.connect(self._on_analyze)
        control_layout.addWidget(self._analyze_btn)

        self._refresh_list_btn = QPushButton("刷新自选股列表")
        self._refresh_list_btn.setMinimumHeight(40)
        self._refresh_list_btn.clicked.connect(self._refresh_watchlist_info)
        control_layout.addWidget(self._refresh_list_btn)

        control_layout.addStretch()

        self._watchlist_count_label = QLabel("自选股数量: 0")
        control_layout.addWidget(self._watchlist_count_label)

        right_layout.addWidget(control_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        right_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("准备就绪")
        self._status_label.setStyleSheet("color: #666; font-size: 14px;")
        right_layout.addWidget(self._status_label)

        result_tabs = QTabWidget()

        self._result_table = QTableWidget()
        self._result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._result_table.setMinimumHeight(300)
        self._result_table.itemSelectionChanged.connect(self._on_result_selected)
        result_tabs.addTab(self._result_table, "分析结果")

        self._signal_table = QTableWidget()
        self._signal_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._signal_table.setAlternatingRowColors(True)
        self._signal_table.setEditTriggers(QTableWidget.NoEditTriggers)
        result_tabs.addTab(self._signal_table, "触发信号")

        self._detail_text = QTableWidget()
        self._detail_text.setSelectionBehavior(QTableWidget.SelectRows)
        self._detail_text.setAlternatingRowColors(True)
        self._detail_text.setEditTriggers(QTableWidget.NoEditTriggers)
        result_tabs.addTab(self._detail_text, "因子详情")

        right_layout.addWidget(result_tabs, 1)

        main_splitter.addWidget(right_widget)

        main_splitter.setSizes([450, 750])
        layout.addWidget(main_splitter, 1)

        self._refresh_watchlist_info()

    def _load_strategies(self):
        strategy_names = self._screener.get_strategy_names()
        self._strategy_combo.clear()
        self._strategy_combo.addItems(strategy_names)

        if strategy_names:
            self._on_strategy_changed(0)

    def _on_strategy_changed(self, index: int):
        if index < 0:
            return

        name = self._strategy_combo.currentText()
        strategy = self._screener.get_strategy(name)
        if strategy:
            self._current_strategy = strategy
            self._apply_strategy_to_ui(strategy)

    def _apply_strategy_to_ui(self, strategy: StrategyConfig):
        buy_index = 0 if strategy.buy_logic == 'AND' else 1
        sell_index = 0 if strategy.sell_logic == 'AND' else 1

        self._buy_logic_combo.setCurrentIndex(buy_index)
        self._sell_logic_combo.setCurrentIndex(sell_index)

        for factor_type, factor_config in strategy.factors.items():
            if factor_type in self._factor_widgets:
                self._factor_widgets[factor_type].set_factor_config(factor_config)

    def _get_strategy_from_ui(self) -> StrategyConfig:
        buy_logic = 'AND' if self._buy_logic_combo.currentIndex() == 0 else 'OR'
        sell_logic = 'AND' if self._sell_logic_combo.currentIndex() == 0 else 'OR'

        factors = {}
        for factor_type, widget in self._factor_widgets.items():
            factors[factor_type] = widget.get_factor_config()

        name = self._strategy_combo.currentText() if self._strategy_combo.currentText() else "默认策略"

        return StrategyConfig(
            name=name,
            buy_logic=buy_logic,
            sell_logic=sell_logic,
            factors=factors
        )

    def _on_new_strategy(self):
        existing_names = self._screener.get_strategy_names()
        dialog = StrategyNameDialog(existing_names, self)
        if dialog.exec_() == QDialog.Accepted:
            name = dialog.get_name()
            new_strategy = StrategyConfig(name=name)
            self._screener.save_strategy(new_strategy)
            self._load_strategies()
            index = self._strategy_combo.findText(name)
            if index >= 0:
                self._strategy_combo.setCurrentIndex(index)

    def _on_save_strategy(self):
        if not self._current_strategy:
            QMessageBox.warning(self, "提示", "请先选择或创建一个策略")
            return

        strategy = self._get_strategy_from_ui()
        strategy.name = self._current_strategy.name
        strategy.created_at = self._current_strategy.created_at
        self._screener.save_strategy(strategy)
        self._current_strategy = strategy
        QMessageBox.information(self, "成功", "策略已保存")

    def _on_duplicate_strategy(self):
        if not self._current_strategy:
            QMessageBox.warning(self, "提示", "请先选择一个策略")
            return

        existing_names = self._screener.get_strategy_names()
        default_name = f"{self._current_strategy.name} (副本)"
        dialog = StrategyNameDialog(existing_names, self, default_name)
        if dialog.exec_() == QDialog.Accepted:
            new_name = dialog.get_name()
            new_strategy = self._screener.duplicate_strategy(
                self._current_strategy.name, new_name
            )
            if new_strategy:
                self._load_strategies()
                index = self._strategy_combo.findText(new_name)
                if index >= 0:
                    self._strategy_combo.setCurrentIndex(index)
                QMessageBox.information(self, "成功", "策略已复制")
            else:
                QMessageBox.warning(self, "错误", "复制策略失败")

    def _on_delete_strategy(self):
        if not self._current_strategy:
            QMessageBox.warning(self, "提示", "请先选择一个策略")
            return

        if self._current_strategy.name == "默认策略":
            QMessageBox.warning(self, "提示", "默认策略不能删除")
            return

        reply = QMessageBox.question(
            self, "确认",
            f"确定要删除策略 \"{self._current_strategy.name}\" 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self._screener.delete_strategy(self._current_strategy.name):
                self._load_strategies()
                QMessageBox.information(self, "成功", "策略已删除")
            else:
                QMessageBox.warning(self, "错误", "删除策略失败")

    def _refresh_watchlist_info(self):
        symbols = self._watchlist_manager.watchlist
        self._watchlist_count_label.setText(f"自选股数量: {len(symbols)}")
        self._status_label.setText(f"准备就绪 - 共 {len(symbols)} 只自选股")

    def _on_analyze(self):
        if self._analysis_thread and self._analysis_thread.isRunning():
            QMessageBox.warning(self, "提示", "分析正在进行中，请稍候...")
            return

        symbols = self._watchlist_manager.watchlist
        if not symbols:
            QMessageBox.warning(self, "提示", "自选股列表为空，请先添加股票")
            return

        strategy = self._get_strategy_from_ui()
        enabled_factors = [fc for fc in strategy.factors.values() if fc.enabled]
        if not enabled_factors:
            QMessageBox.warning(self, "提示", "请至少启用一个因子")
            return

        total_weight = sum(fc.weight for fc in enabled_factors)
        if total_weight == 0:
            QMessageBox.warning(self, "提示", "请设置因子权重大于0")
            return

        self._analyze_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, len(symbols))
        self._status_label.setText("开始分析...")

        self._analysis_thread = AnalysisThread(
            self._screener, symbols, strategy
        )
        self._analysis_thread.progress_signal.connect(self._on_analysis_progress)
        self._analysis_thread.finished_signal.connect(self._on_analysis_finished)
        self._analysis_thread.error_signal.connect(self._on_analysis_error)
        self._analysis_thread.start()

    def _on_analysis_progress(self, current: int, total: int, symbol: str):
        self._progress_bar.setValue(current)
        self._status_label.setText(f"正在分析: {symbol} ({current}/{total})")

    def _on_analysis_finished(self, results: List[StockAnalysisResult]):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._current_results = results
        self._display_results(results)
        self._status_label.setText(f"分析完成 - 共 {len(results)} 只股票")

    def _on_analysis_error(self, error_msg: str):
        self._analyze_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"分析出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"分析过程中出错:\n{error_msg}")

    def _display_results(self, results: List[StockAnalysisResult]):
        sorted_results = sorted(
            results,
            key=lambda x: x.match_percent,
            reverse=True
        )

        self._result_table.clear()
        self._result_table.setColumnCount(8)
        self._result_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "当前价格", "匹配度", "买入信号", "卖出信号",
            "总得分", "分析时间"
        ])
        self._result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._result_table.setRowCount(len(sorted_results))
        for row, result in enumerate(sorted_results):
            self._result_table.setItem(row, 0, QTableWidgetItem(result.symbol))
            self._result_table.setItem(row, 1, QTableWidgetItem(result.name))
            self._result_table.setItem(row, 2, QTableWidgetItem(f"${result.current_price:.2f}"))

            match_item = QTableWidgetItem(f"{result.match_percent:.1f}%")
            if result.match_percent >= 80:
                match_item.setForeground(QColor(34, 197, 94))
            elif result.match_percent >= 60:
                match_item.setForeground(QColor(59, 130, 246))
            elif result.match_percent >= 40:
                match_item.setForeground(QColor(251, 191, 36))
            else:
                match_item.setForeground(QColor(239, 68, 68))
            self._result_table.setItem(row, 3, match_item)

            buy_count = len(result.buy_signals)
            buy_item = QTableWidgetItem(f"{buy_count} 个")
            if buy_count > 0:
                buy_item.setForeground(QColor(34, 197, 94))
            self._result_table.setItem(row, 4, buy_item)

            sell_count = len(result.sell_signals)
            sell_item = QTableWidgetItem(f"{sell_count} 个")
            if sell_count > 0:
                sell_item.setForeground(QColor(239, 68, 68))
            self._result_table.setItem(row, 5, sell_item)

            score_item = QTableWidgetItem(
                f"{result.total_score:.1f}/{result.max_total_score:.1f}"
            )
            self._result_table.setItem(row, 6, score_item)

            try:
                analysis_time = datetime.fromisoformat(result.analysis_time)
                time_str = analysis_time.strftime('%H:%M:%S')
            except:
                time_str = result.analysis_time
            self._result_table.setItem(row, 7, QTableWidgetItem(time_str))

        self._display_signals(sorted_results)

    def _display_signals(self, results: List[StockAnalysisResult]):
        signal_rows = []
        for result in results:
            for signal in result.buy_signals:
                signal_rows.append({
                    'symbol': result.symbol,
                    'name': result.name,
                    'type': '买入',
                    'signal': signal,
                    'match_percent': result.match_percent
                })
            for signal in result.sell_signals:
                signal_rows.append({
                    'symbol': result.symbol,
                    'name': result.name,
                    'type': '卖出',
                    'signal': signal,
                    'match_percent': result.match_percent
                })

        signal_rows.sort(key=lambda x: x['match_percent'], reverse=True)

        self._signal_table.clear()
        self._signal_table.setColumnCount(5)
        self._signal_table.setHorizontalHeaderLabels([
            "股票代码", "名称", "信号类型", "触发原因", "匹配度"
        ])
        self._signal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self._signal_table.setRowCount(len(signal_rows))
        for row, signal_data in enumerate(signal_rows):
            self._signal_table.setItem(row, 0, QTableWidgetItem(signal_data['symbol']))
            self._signal_table.setItem(row, 1, QTableWidgetItem(signal_data['name']))

            type_item = QTableWidgetItem(signal_data['type'])
            if signal_data['type'] == '买入':
                type_item.setForeground(QColor(34, 197, 94))
            else:
                type_item.setForeground(QColor(239, 68, 68))
            self._signal_table.setItem(row, 2, type_item)

            self._signal_table.setItem(row, 3, QTableWidgetItem(signal_data['signal']))
            self._signal_table.setItem(row, 4, QTableWidgetItem(f"{signal_data['match_percent']:.1f}%"))

    def _on_result_selected(self):
        selected = self._result_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        symbol_item = self._result_table.item(row, 0)
        if not symbol_item:
            return

        symbol = symbol_item.text()
        result = None
        for r in self._current_results:
            if r.symbol == symbol:
                result = r
                break

        if result:
            self._display_factor_details(result)

    def _display_factor_details(self, result: StockAnalysisResult):
        self._detail_text.clear()
        self._detail_text.setColumnCount(6)
        self._detail_text.setHorizontalHeaderLabels([
            "因子类型", "是否启用", "得分", "满分", "得分率", "触发条件"
        ])
        self._detail_text.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        factor_results = list(result.factor_results.values())
        self._detail_text.setRowCount(len(factor_results))

        for row, fr in enumerate(factor_results):
            self._detail_text.setItem(row, 0, QTableWidgetItem(self._get_factor_display_name(fr.factor_type)))
            self._detail_text.setItem(row, 1, QTableWidgetItem("是" if fr.enabled else "否"))

            score_item = QTableWidgetItem(f"{fr.score:.1f}")
            if fr.is_buy_signal:
                score_item.setForeground(QColor(34, 197, 94))
            elif fr.is_sell_signal:
                score_item.setForeground(QColor(239, 68, 68))
            self._detail_text.setItem(row, 2, score_item)

            self._detail_text.setItem(row, 3, QTableWidgetItem(f"{fr.max_score:.1f}"))

            norm_item = QTableWidgetItem(f"{fr.normalized_score:.1f}%")
            self._detail_text.setItem(row, 4, norm_item)

            condition_item = QTableWidgetItem(fr.trigger_condition if fr.trigger_condition else "--")
            self._detail_text.setItem(row, 5, condition_item)

    def _get_factor_display_name(self, factor_type: str) -> str:
        names = {
            'MA': "MA均线",
            'RSI': "RSI",
            'MACD': "MACD",
            'BOLLINGER': "布林带",
            'KDJ': "KDJ",
            'PE': "PE估值"
        }
        return names.get(factor_type, factor_type)

    def refresh(self):
        self._refresh_watchlist_info()
