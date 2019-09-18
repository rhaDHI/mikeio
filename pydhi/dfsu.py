import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import System
from System import Array
from DHI.Generic.MikeZero import eumUnit, eumQuantity
from DHI.Generic.MikeZero.DFS import DfsFileFactory, DfsFactory, DfsSimpleType, DataValueType
from DHI.Generic.MikeZero.DFS.dfsu import DfsuFile, DfsuFileType
from pydhi.dutil import to_numpy

from pydhi.helpers import safe_length

class dfsu():


    def read(self, dfsufile, item_numbers=None):
        """ Function: Read a dfsu file

        usage:
            [data, time, name] = read(filename, item_numbers)
            item_numbers is a list of indices (base 0) to read from

        Returns
            1) the data contained in a dfsu file in a list of numpy matrices
            2) time index
            3) name of the items

        NOTE
            Returns data (x, nt)
        """

        # Open the dfs file for reading
        dfs = DfsuFile.Open(dfsufile)
        self._dfs = dfs


        # NOTE. Item numbers are base 0 (everything else in the dfs is base 0)
        item_offset = 1
        n_items = safe_length(dfs.ItemInfo)

        # Dynamic Z is the first item in 3d files
        if (dfs.DfsuFileType == DfsuFileType.Dfsu3DSigma) or (dfs.DfsuFileType == DfsuFileType.Dfsu3DSigmaZ):
            item_offset = 2
            n_items = n_items -1

        if item_numbers is None:
            item_numbers = list(range(n_items))
        else:
            n_items = len(item_numbers)


        xNum = dfs.NumberOfElements
        nt = dfs.NumberOfTimeSteps

        deleteValue = dfs.DeleteValueFloat


        data_list = []

        for item in range(n_items):
            # Initialize an empty data block
            data = np.ndarray(shape=(xNum, nt), dtype=float)
            data_list.append(data)

        t = []
        startTime = dfs.StartDateTime;
        for it in range(nt):
            for item in range(n_items):

                itemdata = dfs.ReadItemTimeStep(item_numbers[item] + item_offset, it)

                src = itemdata.Data

                d = to_numpy(src)

                d[d == deleteValue] = np.nan
                data_list[item][:, it] = d

            t.append(startTime.AddSeconds(itemdata.Time).ToString("yyyy-MM-dd HH:mm:ss"))

        time = pd.DatetimeIndex(t)
        names = []
        for item in range(n_items):
            name = dfs.ItemInfo[item].Name
            names.append(name)

        dfs.Close()
        return (data_list, time, names)


    def write(self, dfsufile, data):
        """
        Function: write to a pre-created dfsu file.

        dfsufile:
            full path and filename to existing dfs2 file

        data:
            list of matrices. len(data) must equal the number of items in the dfs2.
            Easch matrix must be of dimension y,x,time

        usage:
            write(filename, data) where  data(x, nt)

        Returns:
            Nothing

        """

        # Open the dfs file for writing
        dfs = DfsFileFactory.DfsGenericOpenEdit(dfsufile)

        n_time_steps = dfs.FileInfo.TimeAxis.NumberOfTimeSteps
        n_items = safe_length(dfs.ItemInfo)

        deletevalue = dfs.FileInfo.DeleteValueFloat

        for i in range(n_time_steps):
            for item in range(n_items):
                d = data[item][:, i]
                d[np.isnan(d)] = deletevalue
                darray = Array[System.Single](np.array(d.reshape(d.size, 1)[:, 0]))
                dfs.WriteItemTimeStepNext(0, darray)

        dfs.Close()

    def get_element_coords(self):
        ne = self._dfs.NumberOfElements

        # Node coordinates
        xn = np.array(list(self._dfs.X))
        yn = np.array(list(self._dfs.Y))
        zn = np.array(list(self._dfs.Z))

        ec = np.empty([ne,3])

        for j in range(ne):
            nodes = self._dfs.ElementTable[j]

            xcoords = np.empty(nodes.Length)
            ycoords = np.empty(nodes.Length)
            zcoords = np.empty(nodes.Length)
            for i in range(nodes.Length):
                nidx = nodes[i]-1
                xcoords[i] = xn[nidx]
                ycoords[i] = yn[nidx]
                zcoords[i] = zn[nidx]

            ec[j,0] = xcoords.mean()
            ec[j,1] = ycoords.mean()
            ec[j,2] = zcoords.mean()

        return ec


    def find_closest_element_index(self, x, y, z=None):

        ec = self.get_element_coords()

        if z is None:
            poi = np.array([x,y])

            d = ((ec[:,0:2] - poi)**2).sum(axis=1)
            idx = d.argsort()[0]
        else:
            poi = np.array([x, y, z])

            d = ((ec - poi)**2).sum(axis=1)
            idx = d.argsort()[0]

        return idx




