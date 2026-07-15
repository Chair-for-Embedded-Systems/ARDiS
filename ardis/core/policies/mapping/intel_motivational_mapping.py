from ardis.core.mapping import *

class IntelMotivationalExample(MappingPolicy):
    def __init__(self, e_core_first = True):
        super().__init__()
        self.__e_core_first = e_core_first

    def executeMapping(self, applications):
        next = 0
        # default mapping: next available core
        for app in applications:
            if "omnetpp" in app:                
                self._mapping[app] = intel_e_core_ids[0] if self.__e_core_first else intel_p_core_ids[0]
            else:
                self._mapping[app] = intel_p_core_ids[next] if self.__e_core_first else intel_e_core_ids[next]
                next += 1
        return self._mapping