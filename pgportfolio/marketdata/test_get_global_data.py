from pgportfolio.marketdata.datamatrices import DataMatrices
from pgportfolio.marketdata.globaldatamatrix import HistoryManager
from pgportfolio.tools.configprocess import load_config


config = load_config(67)

data_matris = DataMatrices.create_from_config(config)

panel = data_matris.global_matrix

print(panel.shape)
print(panel['close'])
print(panel['low'])
print(panel['high'])
print(panel.minor_axis)


data_matris._update_data_matrix()

print(panel.shape)
print(panel['close'])
print(panel['low'])
print(panel['high'])
print(panel.minor_axis)
# print(panel.values[0][0][-1])

# data_matris._update_data_matrix()
#
# print(panel.shape)
# print(panel.size)
# print(panel.values[0])
# print(panel.values[0][0])
# print(panel.values[0][0][-1])