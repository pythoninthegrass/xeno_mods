using System.Collections.Generic;

namespace X2LoadProfiler {

    // Reports the first read of each item since it was last released, so a trace logs one line per load generation
    public class FirstReadTracker<T> {

        private readonly HashSet<T> _read = new HashSet<T>();

        public bool Read(T item) {
            return _read.Add(item);
        }

        public void Release(T item) {
            _read.Remove(item);
        }
    }

}
