import json

from config import FileHandler

class Gasmeter():
    def __init__(self, file: str):
        self.filename = file
        self.values = self._read_values()

    def _read_values(self) -> dict:
        try:
            return json.loads(FileHandler(self.filename).read())
        except OSError:
            defaults: dict = {"gasm3": 1000.00, "gaskWh": 1000.00, "brennzahl": 11.537 , "zustandszahl": 0.95, "impulsm3": 0.01}
            FileHandler(self.filename).write(json.dumps(defaults))
        return json.loads(FileHandler(self.filename).read())

    def write_values(self) -> None:
        FileHandler(self.filename).write(json.dumps(self.values))

    def do_counting(self):
        self._count_up()
        self.calc_power()
        self.write_values()

    def _count_up(self) -> float:
        """method for trying to prevent floating point error.

        convert as string to integer without any calculation and count up
        """
        imp_str: str = str(self.values["impulsm3"])
        _decimal = imp_str[imp_str.index(".")+1:]
        decimal = len(_decimal)

        multiplier = 10**decimal
        str_formatter = f'{{:.{decimal}f}}'
        _m3_str = str_formatter.format(self.values["gasm3"])
        m3_str = _m3_str.replace(".", "")

        result = int(int(m3_str) + (self.values["impulsm3"] * multiplier))
        self.values["gasm3"] =  result / multiplier

    def calc_power(self) -> float:
        """
        calculation m3 to kWh
        """
        self.values["gaskWh"] = self.values["gasm3"] * self.values['brennzahl'] * self.values['zustandszahl']
