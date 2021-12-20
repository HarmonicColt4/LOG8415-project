import matplotlib.pyplot as pyplot
import sys
import glob
import os

def main():

    if not os.path.exists('powerapi-plots'):
        os.makedirs('powerapi-plots')

    files = glob.glob('results/powerapi*')

    for path in files:
        values = []
        timestamps = []

        filename = path[path.find('\\') + 1:]
        filename_no_ext = filename[:-4]

        with open(path, 'r') as f:
            lines = f.readlines()
            seconds = 0.5
            for line in lines:
                line = line.strip('\n')
                id, timestamp, target, devices, power = line.split(';')
                value = power[power.find('=')+1:power.find(' ')]
                value = float(value)
                values.append(value)
                timestamps.append(seconds)
                seconds += 0.5
        
        words = filename_no_ext.split('_')

        title = ''

        if len(words) == 2:
            title = f'Power consumption of {words[1]}'
        
        if len(words) == 3:
            title = f'Power consumption of {words[1]} with {words[2]}'

        fig = pyplot.figure()
        fig.suptitle(title)

        ax = fig.add_subplot(111) # subplot(nbcol, nbligne, numfigure)
        ax.plot(timestamps, values)
        ax.set_xlabel('Timestamp')
        ax.set_ylabel('Consommation (mJ)')
        pyplot.tight_layout()
        pyplot.subplots_adjust(top=0.9)



        output_filename = f'powerapi-plots/{filename_no_ext}.jpg'

        fig.savefig(output_filename)

if __name__ == '__main__':
    main()