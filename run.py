import argparse
from util import data, fig, launch

# ----------------------------------------------------------------------------

def make_parser():
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers(title='Commands')

  # train

  train_parser = subparsers.add_parser('train', help='Train model')
  train_parser.set_defaults(func=train)

  train_parser.add_argument('--dataset', default='mnist')
  train_parser.add_argument('--model', default='softmax')
  train_parser.add_argument('-e', '--epochs', type=int, default=10)
  train_parser.add_argument('-l', '--logname', default='mnist-run')
  train_parser.add_argument('--alg', default='adam')
  train_parser.add_argument('--lr', type=float, default=1e-3)
  train_parser.add_argument('--b1', type=float, default=0.9)
  train_parser.add_argument('--b2', type=float, default=0.999)
  train_parser.add_argument('--n_batch', type=int, default=128)
  train_parser.add_argument('--n_superbatch', type=int, default=1280)

  # plot

  plot_parser = subparsers.add_parser('plot', help='Plot logfile')
  plot_parser.set_defaults(func=plot)

  plot_parser.add_argument('logfiles', metavar='log', nargs='+')
  plot_parser.add_argument('--type', default='two', 
                           choices=['two', 'many', 'one-vs-many', 'many-vs-many'])
  plot_parser.add_argument('--out', required=True)
  plot_parser.add_argument('--double', nargs='+', default=[0], type=int)
  plot_parser.add_argument('--col', type=int, default=2)
  plot_parser.add_argument('--log2', nargs='+') 

  # grid

  grid_parser = subparsers.add_parser('grid', 
    help='Print command for hyperparameter grid search')
  grid_parser.set_defaults(func=grid)

  grid_parser.add_argument('--dataset', default='mnist')
  grid_parser.add_argument('--model', default='softmax')
  grid_parser.add_argument('-e', '--epochs', type=int, default=10)
  grid_parser.add_argument('-l', '--logname', default='mnist-run')
  grid_parser.add_argument('--alg', nargs='+')
  grid_parser.add_argument('--lr', type=float, default=[1e-3], nargs='+')
  grid_parser.add_argument('--b1', type=float, default=[0.9], nargs='+')
  grid_parser.add_argument('--b2', type=float, default=[0.999], nargs='+')
  grid_parser.add_argument('--n_batch', type=int, default=[100], nargs='+')

  return parser

# ----------------------------------------------------------------------------

def train(args):
  import models
  import numpy as np
  np.random.seed(1234)

  if args.dataset == 'mnist':
    n_dim, n_out, n_channels = 28, 10, 1
    X_train, Y_train, X_val, Y_val, _, _ = data.load_mnist()
  elif args.dataset == 'cifar10':
    n_dim, n_out, n_channels = 32, 10, 3
    X_train, Y_train, X_val, Y_val = data.load_cifar10()
    X_train, X_val = data.whiten(X_train, X_val)
  else:
    X_train, Y_train = data.load_h5(args.train)
    X_val, Y_val = data.load_h5(args.test)
    # also get the data dimensions
  print 'dataset loaded.'

  # set up optimization params
  p = { 'lr' : args.lr, 'b1': args.b1, 'b2': args.b2 }

  # create model
  if args.model == 'softmax':
    model = models.Softmax(n_dim=n_dim, n_out=n_out, n_superbatch=args.n_superbatch, 
                           opt_alg=args.alg, opt_params=p)
  elif args.model == 'mlp':
    model = models.MLP(n_dim=n_dim, n_out=n_out, n_superbatch=args.n_superbatch, 
                       opt_alg=args.alg, opt_params=p)
  elif args.model == 'cnn':
    model = models.CNN(n_dim=n_dim, n_out=n_out, n_chan=n_channels, model=args.dataset,
                       n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)  
  elif args.model == 'resnet':
    model = models.Resnet(n_dim=n_dim, n_out=n_out, n_chan=n_channels,
                          n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)    
  elif args.model == 'vae':
    model = models.VAE(n_dim=n_dim, n_out=n_out, n_chan=n_channels,
                          n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)    
  elif args.model == 'sbn':
    model = models.SBN(n_dim=n_dim, n_out=n_out, n_chan=n_channels,
                          n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)      
  elif args.model == 'adgm':
    model = models.ADGM(n_dim=n_dim, n_out=n_out, n_chan=n_channels,
                          n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)        
  elif args.model == 'dadgm':
    model = models.DADGM(n_dim=n_dim, n_out=n_out, n_chan=n_channels,
                          n_superbatch=args.n_superbatch, opt_alg=args.alg, opt_params=p)          
  else:
    raise ValueError('Invalid model')
  
  # train model
  model.fit(X_train, Y_train, X_val, Y_val, 
            n_epoch=args.epochs, n_batch=args.n_batch,
            logname=args.logname)

def plot(args):
  curves = []
  for f in args.logfiles:
    x, y = fig.parselog(f, yi=args.col)
    curves.append( (x,y) )

  if args.type == 'two':
    fig.plot_many(args.out, curves, names=[], double=args.double)
  elif args.type == 'many':
    fig.plot_many(args.out, curves, args.logfiles, double=args.double)
  elif args.type == 'one-vs-many':
    main_curve = curves[0]
    other_curves = curves[1:]
    double_main = True if args.double else False
    fig.plot_one_vs_many(args.out, main_curve, other_curves, double_main)
  elif args.type == 'many-vs-many':
    curves2 = []
    for f in args.log2:
      x, y = fig.parselog(f, yi=args.col)
      curves2.append( (x,y) )
    double1, double2 = (0 in args.double), (1 in args.double)
    fig.plot_many_vs_many(args.out, curves, curves2, double1, double2)

def grid(args):
  launch.print_grid(args)

def main():
  parser = make_parser()
  args = parser.parse_args()
  args.func(args)

if __name__ == '__main__':
  main()